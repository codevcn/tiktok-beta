import os
import subprocess
import pysubs2
from pysubs2.common import Alignment
from utils.helpers import run_ffmpeg_with_progress


def _build_burn_command(
    video_in_path: str,
    ass_escaped: str,
    video_out_path: str,
    encoder_args: list[str],
) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-i",
        video_in_path,
        "-vf",
        f"ass='{ass_escaped}'",
        *encoder_args,
        "-c:a",
        "copy",
        video_out_path,
    ]


def _is_valid_video_file(path: str) -> bool:
    """Return True when ffprobe can read at least one video stream."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return False

    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_type",
        "-of",
        "csv=p=0",
        path,
    ]

    try:
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ):
        return False

    return any(line.strip() == "video" for line in result.stdout.splitlines())


def _file_signature(path: str) -> tuple[int, int] | None:
    if not os.path.exists(path):
        return None
    stat_result = os.stat(path)
    return (stat_result.st_mtime_ns, stat_result.st_size)


def _run_gpu_burn_with_safe_exit(command: list[str], video_out_path: str) -> bool:
    """
    Run NVENC burn. If FFmpeg exits non-zero after producing a valid video,
    accept the output as a GPU cleanup/teardown issue and continue safely.
    """
    previous_signature = _file_signature(video_out_path)

    try:
        run_ffmpeg_with_progress(command, "Burn subtitle (GPU)")
        return True
    except subprocess.CalledProcessError as e:
        print("  [GPU burn warning] FFmpeg/NVENC failed.")
        print(e.stderr)

        current_signature = _file_signature(video_out_path)
        output_was_updated = current_signature is not None
        output_was_updated = (
            output_was_updated and current_signature != previous_signature
        )

        if output_was_updated and _is_valid_video_file(video_out_path):
            print(
                "  [GPU burn warning] FFmpeg returned an error, but output video "
                "is valid -> keeping GPU result."
            )
            return True

        print("  -> GPU output is missing or invalid -> falling back to CPU encode.")
        return False


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
    use_gpu: bool = False,
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
    # GIAI DOAN 2: BURN ASS SUBTITLE (GPU WITH CPU FALLBACK)
    # ==========================================
    ass_abs = os.path.abspath(ass_path)
    ass_escaped = ass_abs.replace("\\", "/").replace(":", "\\:")

    gpu_encoder_args = ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "23"]
    cpu_encoder_args = ["-c:v", "libx264", "-preset", "fast", "-crf", "23"]
    gpu_command = _build_burn_command(
        video_in_path,
        ass_escaped,
        video_out_path,
        gpu_encoder_args,
    )
    cpu_command = _build_burn_command(
        video_in_path,
        ass_escaped,
        video_out_path,
        cpu_encoder_args,
    )

    try:
        if use_gpu:
            print("  -> Encoder: h264_nvenc (GPU), fallback CPU if unavailable")
            if not _run_gpu_burn_with_safe_exit(gpu_command, video_out_path):
                print("  -> Encoder: libx264 (CPU fallback)")
                run_ffmpeg_with_progress(cpu_command, "Burn subtitle (CPU fallback)")
        else:
            print("  -> Encoder: libx264 (CPU)")
            run_ffmpeg_with_progress(cpu_command, "Burn subtitle")
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
