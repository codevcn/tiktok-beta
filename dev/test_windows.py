"""
Test script for converting a video to 9:16 with FFmpeg on Windows only.
"""

import subprocess
import threading
import time
import re
import sys


def read_stderr(process, total_duration):
    time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})")
    for line in process.stderr:
        match = time_pattern.search(line)
        if match:
            cur_sec = sum(
                x * f for x, f in zip(map(float, match.groups()), [3600, 60, 1])
            )
            progress = min((cur_sec / total_duration) * 100, 99.9)
            sys.stdout.write(
                f"\rTiến trình: {progress:>5.1f}% | {cur_sec:.2f}s / {total_duration:.2f}s"
            )
            sys.stdout.flush()


def convert_916(input_file, output_file, top_text, bottom_text, platform="windows"):
    # Lấy thời lượng
    probe_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        input_file,
    ]
    total_duration = float(subprocess.check_output(probe_cmd).strip())

    # Cấu hình theo platform
    if platform == "windows":
        font_path = "C\\:/Windows/Fonts/arial.ttf"
        encoder_opts = [
            "-c:v",
            "h264_amf",
            "-rc",
            "cqp",
            "-qp_i",
            "19",
            "-qp_p",
            "19",
            "-quality",
            "quality",
        ]
    else:  # macOS
        font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
        encoder_opts = ["-c:v", "h264_videotoolbox", "-b:v", "8M"]

    target_w, target_h = 1080, 1920
    video_h = 608
    pad_h = (target_h - video_h) // 2

    # ✅ Fix 1: loop=9999 thay vì loop=-1
    filter_complex = (
        f"[0:v]split=2[main][temp];"
        f"[temp]trim=start_frame=0:end_frame=1,"
        f"loop=loop=9999:size=1,setpts=PTS-STARTPTS,"
        # ============================================
        # ĐIỀU CHỈNH ĐỘ MỜ Ở ĐÂY
        # boxblur=RADIUS:POWER
        # RADIUS: số càng lớn càng mờ (mặc định 15, tối đa ~60)
        # POWER:  số lần áp dụng blur (thường để 1-3)
        # Ví dụ nhẹ: boxblur=15:1
        # Ví dụ mờ vừa: boxblur=30:2
        # Ví dụ rất mờ: boxblur=50:3
        # ============================================
        f"boxblur=25:1,"  # ← CHỈNH SỐ NÀY
        f"split=2[blurred1][blurred2];"
        f"[blurred1]scale={target_w}:{pad_h}:force_original_aspect_ratio=increase,"
        f"crop={target_w}:{pad_h}[tp];"
        f"[blurred2]scale={target_w}:{pad_h}:force_original_aspect_ratio=increase,"
        f"crop={target_w}:{pad_h}[bp];"
        f"[main]scale={target_w}:{video_h}[mid];"
        f"[tp][mid][bp]vstack=inputs=3[combined];"
        f"[combined]"
        f"drawtext=text='{top_text}':fontcolor=white:fontsize=70"
        f":x=(w-text_w)/2:y=({pad_h}-text_h)/2:fontfile='{font_path}',"
        f"drawtext=text='{bottom_text}':fontcolor=white:fontsize=60"
        f":x=(w-text_w)/2:y=h-({pad_h}+text_h)/2:fontfile='{font_path}'[v]"
    )

    cmd = [
        "ffmpeg",
        "-i",
        input_file,
        "-filter_complex",
        filter_complex,
        "-map",
        "[v]",
        "-map",
        "0:a?",
        *encoder_opts,
        "-c:a",
        "copy",
        "-shortest",
        "-movflags",
        "+faststart",
        output_file,
        "-y",
    ]

    start_time = time.time()

    # ✅ Fix 2: Đọc stderr bằng thread riêng — tránh deadlock
    process = subprocess.Popen(
        cmd, stderr=subprocess.PIPE, universal_newlines=True, encoding="utf-8"
    )

    stderr_thread = threading.Thread(
        target=read_stderr, args=(process, total_duration), daemon=True
    )
    stderr_thread.start()

    # ✅ Fix 3: Timeout động theo độ dài video
    dynamic_timeout = total_duration * 3 + 120  # Thêm 120s buffer cho GPU flush
    try:
        process.wait(timeout=dynamic_timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        print(
            f"\n⚠️ GPU encoder timeout sau {dynamic_timeout:.0f}s! Thử lại với CPU (libx264)..."
        )
        return

    stderr_thread.join(timeout=5)

    elapsed = time.time() - start_time
    if process.returncode == 0:
        print(f"\n✅ Hoàn thành! Thời gian: {elapsed:.2f}s")
    else:
        print(f"\n❌ FFmpeg lỗi! Return code: {process.returncode}")


# ========== Chạy thử ==========
if __name__ == "__main__":
    convert_916(
        input_file="input.mp4",
        output_file="output.mp4",
        top_text="Tiêu đề trên",
        bottom_text="Tiêu đề dưới",
        platform="windows",  # Đổi thành "macos" nếu dùng Mac
    )
