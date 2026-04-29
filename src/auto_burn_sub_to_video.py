"""
Pipeline tự động xử lý video từ flow-inputs.json.

Mỗi link có thể có nhiều flow xử lý tuần tự.
Các bước chung (download, xóa watermark, tách audio, transcribe, sửa typo)
chỉ chạy MỘT LẦN. Sau đó từng flow chạy riêng phần dịch/burn subtitle,
và mỗi flow đều xuất phát từ video gốc (sau download + xóa watermark).

[link từ flow-inputs.json]
    --> [download video bằng yt-dlp]
    --> [xóa watermark bằng ffmpeg delogo]  (*nếu có cấu hình watermark)
    --> [tách audio]
    --> [transcribe audio → SRT thô]
    --> [sửa lỗi chính tả SRT bằng AI]
    --> Với mỗi flow trong danh sách flows:
        --> [dịch SRT sang ngôn ngữ đích bằng AI]  (*nếu flow có translate)
        --> [burn ASS subtitle vào video gốc]
"""

import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from features.extract_audio_from_video import extract_audio_lossless
from features.transcribe_audio_file import transcribe_audio
from features.fix_transcribe_typos import fix_typos_in_srt
from features.translate_srt import translate_srt
from features.burn_ass_subtitle import burn_subtitle_to_video
from features.remove_watermark import remove_watermark
from utils.helpers import download_video, extract_video_id, load_env, load_links_config


# ============================================================
# TIỆN ÍCH ĐO THỜI GIAN
# ============================================================


def _fmt_duration(seconds: float) -> str:
    """Chuyển giây thành chuỗi dễ đọc: 1h 23m 45s hoặc 12.3s."""
    if seconds >= 3600:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h}h {m:02d}m {s:02d}s"
    elif seconds >= 60:
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m}m {s:02d}s"
    else:
        return f"{seconds:.1f}s"


@contextmanager
def _timed_step(name: str, timings: list):
    """Context manager đo thời gian một bước và lưu vào danh sách timings."""
    t0 = time.perf_counter()
    yield
    elapsed = time.perf_counter() - t0
    timings.append((name, elapsed))
    print(f"  ⏱  {name}: {_fmt_duration(elapsed)}")


def _print_timing_summary(timings: list) -> None:
    """In bảng tổng kết thời gian thực thi từng bước."""
    total = sum(t for _, t in timings)
    width = max(len(n) for n, _ in timings) + 2
    print(f"\n{'─' * (width + 20)}")
    print(f"  📊  THỜI GIAN THỰC THI TỪNG BƯỚC")
    print(f"{'─' * (width + 20)}")
    for name, elapsed in timings:
        pct = elapsed / total * 100 if total > 0 else 0
        bar = "█" * int(pct / 5)  # mỗi █ ≈ 5%
        print(f"  {name:<{width}} {_fmt_duration(elapsed):>8}  {bar} {pct:.0f}%")
    print(f"{'─' * (width + 20)}")
    print(f"  {'TỔNG CỘNG':<{width}} {_fmt_duration(total):>8}")
    print(f"{'─' * (width + 20)}\n")


# ============================================================
# MAP TÊN FLOW → CÓ DỊCH HAY KHÔNG
# ============================================================

FLOW_TRANSLATE_MAP: dict[str, bool] = {
    "burn_sub_to_video_with_translate": True,
    "burn_sub_to_video_no_translate": False,
}


# ============================================================
# PIPELINE XỬ LÝ MỘT LINK (MULTI-FLOW)
# ============================================================


def process_one_link(link_entry: dict, base_output_dir: str, use_gpu: bool) -> None:
    """
    Chạy pipeline cho một link với nhiều flow tuần tự.

    Các bước chung (download, watermark, audio, transcribe, fix typo)
    chỉ chạy 1 lần. Mỗi flow sau đó chạy riêng phần dịch/burn subtitle
    và đều xuất phát từ video gốc (sau download + xóa watermark).

    Args:
        link_entry: Một phần tử trong mảng "links" của flow-inputs.json.
        base_output_dir: Thư mục gốc để lưu kết quả (data/video/output).
        use_gpu: True → dùng GPU cho transcribe và encode.
    """
    link = link_entry["link"]
    original_lang_code = link_entry.get("original_lang_code")  # None = tự detect
    target_lang_code = link_entry.get("target_lang_code", "vi")
    subtitle_configs = link_entry.get("subtitle_configs", {})
    watermark_config = link_entry.get("watermark")  # None nếu không có field này
    flows = link_entry.get("flows", [])

    if not flows:
        print("⚠️  Không có flow nào được cấu hình cho link này → bỏ qua.")
        return

    # Tạo thư mục output riêng cho link này theo timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_id = extract_video_id(link)
    output_dir = os.path.join(base_output_dir, f"vid-{video_id}-{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n📁 Thư mục đầu ra: {output_dir}")

    # Thư mục tạm để download video
    download_dir = os.path.join(output_dir, "download")
    os.makedirs(download_dir, exist_ok=True)

    # Định nghĩa đường dẫn các file trung gian (phần chung)
    video_no_wm_path = os.path.join(output_dir, "video_no_watermark.mp4")
    audio_tmp_path = os.path.join(output_dir, "audio_tmp.m4a")
    srt_raw_path = os.path.join(output_dir, "raw_subtitle.srt")
    srt_fixed_path = os.path.join(output_dir, "fixed_subtitle.srt")

    timings: list[tuple[str, float]] = []

    # ============================================================
    # PHẦN CHUNG — chỉ chạy 1 lần
    # ============================================================

    # --- Bước 0: Tải video ---
    print("\n--- BƯỚC 0: TẢI VIDEO ---")
    with _timed_step("Tải video", timings):
        video_in_path = download_video(link, download_dir)

    # --- Bước 1: Xóa watermark (nếu có cấu hình) ---
    if watermark_config:
        print("\n--- BƯỚC 1: XÓA WATERMARK ---")
        with _timed_step("Xóa watermark", timings):
            remove_watermark(
                video_in_path, video_no_wm_path, watermark_config, use_gpu=use_gpu
            )
        base_video_path = video_no_wm_path
    else:
        print("\nℹ️  Không có cấu hình watermark → bỏ qua bước xóa watermark.")
        base_video_path = video_in_path

    # --- Bước 2: Tách âm thanh ---
    print("\n--- BƯỚC 2: TÁCH ÂM THANH ---")
    with _timed_step("Tách âm thanh", timings):
        extract_audio_lossless(base_video_path, audio_tmp_path)

    # --- Bước 3: Transcribe giọng nói → SRT thô ---
    print("\n--- BƯỚC 3: PHÂN TÍCH GIỌNG NÓI ---")
    with _timed_step("Transcribe", timings):
        transcribe_audio(
            audio_tmp_path, srt_raw_path, language=original_lang_code, use_gpu=use_gpu
        )

    # --- Bước 4: Sửa lỗi chính tả SRT bằng AI ---
    print("\n--- BƯỚC 4: SỬA LỖI CHÍNH TẢ BẰNG AI ---")
    with _timed_step("Sửa typo (AI)", timings):
        fix_typos_in_srt(srt_raw_path, srt_fixed_path)

    # ============================================================
    # PHẦN RIÊNG — lặp qua từng flow
    # ============================================================

    total_flows = len(flows)
    print(f"\n{'═' * 60}")
    print(f"  📋 Tổng số flow cần chạy: {total_flows}")
    print(f"{'═' * 60}")

    for flow_idx, flow_entry in enumerate(flows, 1):
        flow_name = flow_entry.get("name", "")
        do_translate = FLOW_TRANSLATE_MAP.get(flow_name)

        if do_translate is None:
            print(f"\n  ⚠️  Flow không hợp lệ: '{flow_name}' → bỏ qua.")
            print(f"      Các flow hợp lệ: {list(FLOW_TRANSLATE_MAP.keys())}")
            continue

        flow_label = f"FLOW {flow_idx}/{total_flows}"
        print(f"\n{'─' * 60}")
        print(f"  🔄 {flow_label}: {flow_name}")
        print(f"{'─' * 60}")

        # Tên file output riêng cho flow này
        flow_suffix = f"flow{flow_idx}_{flow_name}"
        video_out_path = os.path.join(output_dir, f"output_{flow_suffix}.mp4")

        if do_translate:
            # Dịch SRT → burn
            srt_translated_path = os.path.join(
                output_dir, f"translated_subtitle_{flow_suffix}.srt"
            )
            print(
                f"\n  --- {flow_label} | DỊCH THUẬT SANG [{target_lang_code.upper()}] ---"
            )
            with _timed_step(
                f"[{flow_label}] Dịch thuật → {target_lang_code}", timings
            ):
                translate_srt(srt_fixed_path, srt_translated_path, target_lang_code)
            srt_for_burn = srt_translated_path
        else:
            print(f"\n  ℹ️  {flow_label}: Không dịch thuật → dùng SRT đã sửa typo.")
            srt_for_burn = srt_fixed_path

        # Burn phụ đề vào video gốc (base_video_path)
        print(f"\n  --- {flow_label} | GHÉP PHỤ ĐỀ VÀO VIDEO ---")
        with _timed_step(f"[{flow_label}] Burn subtitle", timings):
            burn_subtitle_to_video(
                srt_for_burn, base_video_path, video_out_path, subtitle_configs
            )

        print(f"\n  ✅ {flow_label}: Hoàn tất → {video_out_path}")

    # Dọn dẹp: xóa audio trung gian
    if os.path.exists(audio_tmp_path):
        os.remove(audio_tmp_path)
        print(f"\n🧹 Đã xóa audio trung gian: {audio_tmp_path}")

    # In bảng tổng kết thời gian
    _print_timing_summary(timings)

    print(f"\n🎉 HOÀN TẤT! Kết quả nằm trong: {output_dir}")


# ============================================================
# ENTRY POINT
# ============================================================


def main() -> None:
    """
    Entry point cho pipeline xử lý video.
    Đọc toàn bộ cấu hình từ flow-inputs.json, bao gồm danh sách links
    và flows per-link.
    """
    # 1. Load biến môi trường
    load_env(".env")

    # 2. Đọc file flow-inputs.json
    config_path = os.path.join("data", "video", "input", "flow-inputs.json")
    config = load_links_config(config_path)

    # Đọc cấu hình GPU từ cấp top-level của flow-inputs.json
    use_gpu: bool = bool(config.get("use_gpu", False))
    gpu_label = "GPU (CUDA)" if use_gpu else "CPU"
    print(f"ℹ️  Chế độ xử lý: {gpu_label}")

    links = config.get("links", [])
    if not links:
        print("❌ Không có link nào trong flow-inputs.json để xử lý.")
        sys.exit(1)

    # parallel_execution hiện tại luôn False (xử lý tuần tự)
    # Khi cần xử lý song song sẽ mở rộng ở đây
    base_output_dir = os.path.join("data", "video", "output")
    os.makedirs(base_output_dir, exist_ok=True)

    print(f"📋 Tổng số link cần xử lý: {len(links)}")

    for idx, link_entry in enumerate(links, 1):
        link = link_entry.get("link", "")
        flows = link_entry.get("flows", [])
        flow_names = [f.get("name", "?") for f in flows]

        print(f"\n{'='*60}")
        print(f"🔗 [{idx}/{len(links)}] Đang xử lý: {link}")
        print(f"   Flows: {flow_names}")
        print("=" * 60)

        try:
            process_one_link(link_entry, base_output_dir, use_gpu)
        except Exception as e:
            print(f"\n❌ Lỗi khi xử lý link [{link}]: {e}")
            print("⏭️  Bỏ qua link này, chuyển sang link tiếp theo...")
            continue

    print("\n✅ Đã xử lý xong tất cả các link.")
