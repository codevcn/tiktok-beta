"""
Xóa watermark khỏi video bằng ffmpeg delogo filter.
"""

import os
import subprocess
from features.utils import run_ffmpeg_with_progress


def remove_watermark(video_in_path: str, video_out_path: str, watermark_config: dict) -> str:
    """
    Xóa watermark khỏi video bằng ffmpeg delogo filter.
    Tọa độ từ links.json: x1, y1 (góc trên trái), x2, y2 (góc dưới phải).
    """
    if not os.path.exists(video_in_path):
        raise FileNotFoundError(f"Không tìm thấy file video: {video_in_path}")

    try:
        x1 = int(watermark_config["x1"])
        y1 = int(watermark_config["y1"])
        x2 = int(watermark_config["x2"])
        y2 = int(watermark_config["y2"])
    except KeyError as e:
        raise ValueError(f"Thiếu trường tọa độ watermark: {e}. Cần có: x1, y1, x2, y2.")
    except (TypeError, ValueError) as e:
        raise ValueError(f"Giá trị tọa độ watermark không hợp lệ: {e}")

    w = x2 - x1
    h = y2 - y1

    if w <= 0:
        raise ValueError(f"x2 ({x2}) phải lớn hơn x1 ({x1}).")
    if h <= 0:
        raise ValueError(f"y2 ({y2}) phải lớn hơn y1 ({y1}).")

    print(f"  → Vùng xóa watermark: x={x1}, y={y1}, w={w}, h={h} px")

    command = [
        "ffmpeg", "-y",
        "-i", video_in_path,
        "-vf", f"delogo=x={x1}:y={y1}:w={w}:h={h}",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "copy",
        video_out_path,
    ]

    try:
        run_ffmpeg_with_progress(command, "Xóa watermark")
        print(f"  → Đã lưu: {video_out_path}")
        return video_out_path
    except subprocess.CalledProcessError as e:
        print("❌ FFmpeg báo lỗi khi xóa watermark:")
        print(e.stderr)
        raise
