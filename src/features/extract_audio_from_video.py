import subprocess
from pathlib import Path
from features.utils import run_ffmpeg_with_progress


def extract_audio_lossless(video_path: str, audio_path: str) -> str:
    """
    Tách audio từ video, giữ nguyên chất lượng gốc (copy stream, không re-encode).
    Hiển thị tiến trình % theo thời gian video.
    """
    video_file = Path(video_path)
    output_file = Path(audio_path)

    if not video_file.exists():
        raise FileNotFoundError(f"Không tìm thấy file video: {video_file}")

    command = [
        "ffmpeg", "-y",
        "-i", str(video_file),
        "-vn", "-c:a", "copy",
        str(output_file),
    ]

    try:
        run_ffmpeg_with_progress(command, "Tách audio")
        print(f"  → Đã lưu: {output_file}")
        return str(output_file)
    except subprocess.CalledProcessError as e:
        print("❌ FFmpeg báo lỗi khi tách audio:")
        print(e.stderr)
        raise
