import subprocess
import os
import time
import re


def get_video_duration(input_file):
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        input_file,
    ]
    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
        )
        return float(result.stdout.strip())
    except:
        return 0.0


def convert_916_macos(input_file, output_file, top_text, bottom_text):
    total_duration = get_video_duration(input_file)
    if total_duration == 0:
        print("Lỗi: Không thể đọc được thời lượng video.")
        return

    # --- ĐIỀU CHỈNH CHO MACOS ---
    # Đường dẫn font chữ mặc định trên macOS
    font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
    if not os.path.exists(font_path):
        font_path = "/Library/Fonts/Arial.ttf"  # Đường dẫn dự phòng

    target_w, target_h = 1080, 1920
    video_h = 608
    pad_h = (target_h - video_h) // 2

    filter_complex = (
        f"[0:v]split=2[main][temp];"
        f"[temp]trim=start_frame=0:end_frame=1,loop=loop=-1:size=1,setpts=PTS-STARTPTS,boxblur=15:1[blurred_frame];"
        f"[blurred_frame]scale={target_w}:{pad_h}:force_original_aspect_ratio=increase,crop={target_w}:{pad_h}[top_pad];"
        f"[blurred_frame]scale={target_w}:{pad_h}:force_original_aspect_ratio=increase,crop={target_w}:{pad_h}[bottom_pad];"
        f"[main]scale={target_w}:{video_h}[video_mid];"
        f"[top_pad][video_mid][bottom_pad]vstack=inputs=3[combined];"
        f"[combined]drawtext=text='{top_text}':fontcolor=white:fontsize=70:x=(w-text_w)/2:y=({pad_h}-text_h)/2:fontfile='{font_path}',"
        f"drawtext=text='{bottom_text}':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=h-({pad_h}+text_h)/2:fontfile='{font_path}'[v]"
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
        # --- SỬ DỤNG VIDEOTOOLBOX (GPU MACOS) ---
        "-c:v",
        "h264_videotoolbox",
        "-b:v",
        "10M",  # Đặt bitrate cao để giữ chất lượng (10 Mbps)
        "-realtime",
        "false",  # Ưu tiên chất lượng hơn tốc độ thời gian thực
        "-c:a",
        "copy",
        "-shortest",
        "-movflags",
        "+faststart",
        output_file,
        "-y",
    ]

    print(f"Bắt đầu xử lý trên macOS. Thời lượng: {total_duration}s")
    start_time = time.time()

    process = subprocess.Popen(
        cmd, stderr=subprocess.PIPE, universal_newlines=True, encoding="utf-8"
    )
    time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})")

    if not process.stderr:
        exit(1)

    try:
        while True:
            line = process.stderr.readline()
            if not line and process.poll() is not None:
                break

            match = time_pattern.search(line)
            if match:
                hours, mins, secs = map(float, match.groups())
                current_time_sec = hours * 3600 + mins * 60 + secs
                progress = min((current_time_sec / total_duration) * 100, 100.0)
                print(
                    f"\rĐang render: {progress:>5.1f}% | {current_time_sec:>6.2f}s / {total_duration}s",
                    end="",
                    flush=True,
                )

        process.wait()

        if process.returncode == 0:
            print(
                f"\rĐang render: 100.0% | {total_duration:>6.2f}s / {total_duration}s",
                flush=True,
            )
            elapsed = time.time() - start_time
            print(f"\n\nXử lý hoàn tất!")
            print(f"Tổng thời gian chạy: {int(elapsed//60)} phút {elapsed%60:.2f} giây")
        else:
            print(
                f"\n\nFFmpeg báo lỗi (Mã: {process.returncode}). Kiểm tra lại file đầu vào hoặc bộ lọc."
            )

    except Exception as e:
        print(f"\nLỗi: {e}")
        process.kill()


# --- ĐƯỜNG DẪN TRÊN MACOS ---
# Lưu ý: Mac dùng dấu / cho đường dẫn
input_path = "input.mp4"
output_path = "output_916_mac.mp4"

convert_916_macos(input_path, output_path, "TIÊU ĐỀ MAC", "MÔ TẢ VIDEO")
