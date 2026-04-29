import os
import subprocess
import pysubs2
from pysubs2.common import Alignment
from utils.helpers import run_ffmpeg_with_progress


def _parse_color(color_str: str) -> pysubs2.Color:
    parts = [int(v.strip()) for v in color_str.split(",")]
    if len(parts) == 3:
        return pysubs2.Color(parts[0], parts[1], parts[2])
    elif len(parts) == 4:
        return pysubs2.Color(parts[0], parts[1], parts[2], parts[3])
    else:
        raise ValueError(
            f"Định dạng màu không hợp lệ: '{color_str}'. Dùng 'R,G,B' hoặc 'R,G,B,A'."
        )


def _parse_alignment(alignment_str: str) -> Alignment:
    mapping = {
        "BOTTOM_LEFT": Alignment.BOTTOM_LEFT,
        "BOTTOM_CENTER": Alignment.BOTTOM_CENTER,
        "BOTTOM_RIGHT": Alignment.BOTTOM_RIGHT,
        "MIDDLE_LEFT": Alignment.MIDDLE_LEFT,
        "MIDDLE_CENTER": Alignment.MIDDLE_CENTER,
        "MIDDLE_RIGHT": Alignment.MIDDLE_RIGHT,
        "TOP_LEFT": Alignment.TOP_LEFT,
        "TOP_CENTER": Alignment.TOP_CENTER,
        "TOP_RIGHT": Alignment.TOP_RIGHT,
    }
    key = alignment_str.upper()
    if key not in mapping:
        raise ValueError(
            f"Alignment không hợp lệ: '{alignment_str}'. Hợp lệ: {list(mapping.keys())}"
        )
    return mapping[key]


def burn_subtitle_to_video(
    srt_path: str,
    video_in_path: str,
    video_out_path: str,
    subtitle_configs: dict,
) -> str:
    """
    Burn phụ đề SRT vào video với style từ subtitle_configs (links.json).
    Hiển thị tiến trình % khi ffmpeg encode.
    """
    if not os.path.exists(srt_path):
        raise FileNotFoundError(f"Không tìm thấy file phụ đề: {srt_path}")
    if not os.path.exists(video_in_path):
        raise FileNotFoundError(f"Không tìm thấy file video: {video_in_path}")

    # ==========================================
    # GIAI ĐOẠN 1: TẠO VÀ ĐỊNH DẠNG FILE ASS
    # ==========================================
    print("  → Chuyển đổi SRT → ASS và áp dụng định dạng...")
    ass_path = srt_path.rsplit(".", 1)[0] + ".ass"

    subs = pysubs2.load(srt_path, encoding="utf-8")
    style = subs.styles["Default"]
    style.fontname = subtitle_configs.get("fontname", "Arial")
    style.fontsize = subtitle_configs.get("fontsize", 24)
    style.primarycolor = _parse_color(subtitle_configs.get("primarycolor", "255,255,0"))
    style.outlinecolor = _parse_color(subtitle_configs.get("outlinecolor", "0,0,0"))
    style.backcolor = _parse_color(subtitle_configs.get("backcolor", "0,0,0,128"))
    style.outline = float(subtitle_configs.get("outline", 2.0))
    style.shadow = float(subtitle_configs.get("shadow", 1.0))
    style.bold = bool(subtitle_configs.get("bold", True))
    style.alignment = _parse_alignment(
        subtitle_configs.get("alignment", "BOTTOM_CENTER")
    )
    style.marginv = int(subtitle_configs.get("marginv", 30))
    style.marginl = int(subtitle_configs.get("marginl", 0))
    style.marginr = int(subtitle_configs.get("marginr", 0))

    subs.save(ass_path)
    print(f"  → Đã tạo: {ass_path}")

    # ==========================================
    # GIAI ĐOẠN 2: GHÉP PHỤ ĐỀ ASS BẰNG CPU
    # ==========================================
    ass_abs = os.path.abspath(ass_path)
    ass_escaped = ass_abs.replace("\\", "/").replace(":", "\\:")

    command = [
        "ffmpeg",
        "-y",
        "-i",
        video_in_path,
        "-vf",
        f"ass='{ass_escaped}'",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "copy",
        video_out_path,
    ]

    try:
        run_ffmpeg_with_progress(command, "Burn subtitle")
        print(f"  → Đã lưu: {video_out_path}")
    except subprocess.CalledProcessError as e:
        print("❌ FFmpeg báo lỗi khi burn subtitle:")
        print(e.stderr)
        raise
    finally:
        if os.path.exists(ass_path):
            os.remove(ass_path)
            print(f"  → Đã xóa file ASS tạm: {ass_path}")

    return video_out_path
