import subprocess
import os
import time
import re
import sys


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


def convert_916_macos_fixed(input_file, output_file, top_text, bottom_text):
    total_duration = get_video_duration(input_file)

    # Tìm Font Arial trên Mac
    font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
    if not os.path.exists(font_path):
        font_path = "/Library/Fonts/Arial.ttf"

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
        "-c:v",
        "h264_videotoolbox",  # Sử dụng GPU Mac
        "-b:v",
        "8M",  # Bitrate cao để giữ chất lượng
        "-c:a",
        "copy",
        "-shortest",
        "-movflags",
        "+faststart",  # Giúp đóng file nhanh hơn
        output_file,
        "-y",
    ]

    print(f"--- Bắt đầu render trên macOS ---")
    print(f"File gốc: {total_duration:.2f} giây")
    start_time = time.time()

    # Sử dụng stderr.read(X) để không bị block bởi dấu xuống dòng
    process = subprocess.Popen(
        cmd,
        stderr=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        universal_newlines=True,
        encoding="utf-8",
    )

    time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})")

    if not process.stderr:
        exit(1)

    try:
        while True:
            # Đọc một đoạn dữ liệu từ stderr
            # Chúng ta dùng stderr.read(10) để lấy các đoạn nhỏ liên tục
            output = process.stderr.read(20)
            if not output and process.poll() is not None:
                break

            match = time_pattern.search(output)
            if match:
                hours, mins, secs = map(float, match.groups())
                current_time_sec = hours * 3600 + mins * 60 + secs

                # Tính % và giới hạn 99.9% cho đến khi kết thúc hẳn
                progress = (
                    min((current_time_sec / total_duration) * 100, 99.9)
                    if total_duration > 0
                    else 0
                )
                sys.stdout.write(
                    f"\rTiến trình: {progress:>5.1f}% | Đã xử lý: {current_time_sec:>6.2f}s"
                )
                sys.stdout.flush()

        process.wait()

        # In dòng hoàn tất thực sự
        sys.stdout.write(f"\rTiến trình: 100.0% | Đã xử lý: {total_duration:>6.2f}s\n")

        end_time = time.time()
        elapsed = end_time - start_time
        print(f"\n✅ Xử lý hoàn tất!")
        print(f"⏱️ Tổng thời gian chạy: {int(elapsed//60)} phút {elapsed%60:.2f} giây")

    except KeyboardInterrupt:
        process.kill()
        print("\n🛑 Đã hủy bởi người dùng.")
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")


# --- THAY ĐỔI ĐƯỜNG DẪN TẠI ĐÂY ---
input_path = "input.mp4"
output_path = "output_mac_916.mp4"

convert_916_macos_fixed(input_path, output_path, "TIÊU ĐỀ MAC", "XỬ LÝ TRÊN GPU")
