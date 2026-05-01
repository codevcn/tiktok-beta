"""
Module chuyển đổi video 16:9 thành 9:16.
Tạo 2 lớp phủ tĩnh (blur) trên và dưới video gốc để lấp đầy khung hình 9:16,
kết hợp chèn thêm văn bản ở vùng phủ trống.
"""

import os
import subprocess
import time
import re
import sys


def _get_video_duration(input_file: str) -> float:
    """Lấy tổng thời lượng của video (giây) bằng ffprobe."""
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
    try:
        output = subprocess.check_output(probe_cmd, text=True).strip()
        return float(output)
    except (subprocess.CalledProcessError, ValueError) as e:
        raise RuntimeError(f"Không thể đọc thời lượng video: {e}")


def _run_ffmpeg_with_progress(
    command: list[str], total_duration: float, label: str = "Đang xử lý"
) -> None:
    """Chạy FFmpeg và in ra tiến trình % dựa trên tổng thời lượng."""
    process = subprocess.Popen(
        command,
        stderr=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        universal_newlines=True,
        encoding="utf-8",
        errors="replace",
    )

    time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
    last_pct = -1

    if process.stderr is None:
        raise RuntimeError("Không thể khởi tạo luồng stderr từ FFmpeg.")

    for line in process.stderr:
        match = time_pattern.search(line)
        if match and total_duration > 0:
            h, m, s = match.groups()
            cur_sec = int(h) * 3600 + int(m) * 60 + float(s)
            pct = min(int((cur_sec / total_duration) * 100), 99)
            if pct != last_pct:
                sys.stdout.write(f"\r  ⏳ {label}: {pct:3d}%    ")
                sys.stdout.flush()
                last_pct = pct

    process.wait()
    if process.returncode != 0:
        print()  # Xuống dòng
        raise subprocess.CalledProcessError(process.returncode, command)

    print(f"\r  ✅ {label}: 100%                                    ")


def convert_169_to_916(
    input_file: str,
    output_file: str,
    caption_configs: dict | None = None,
    use_gpu: bool = True,
    platform: str = "windows",
) -> str:
    """
    Hàm chính chuyển đổi video 16:9 sang 9:16.

    Args:
        input_file: Đường dẫn video gốc (16:9).
        output_file: Đường dẫn video đầu ra (9:16).
        caption_configs: Từ điển cấu hình hiển thị văn bản (dải giấy paper strip).
        use_gpu: True nếu muốn sử dụng GPU để encode (tăng tốc độ).
        platform: "windows" hoặc "macos" để cấu hình font và encoder mặc định.

    Returns:
        Đường dẫn file video đầu ra nếu thành công.
    """
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Không tìm thấy file đầu vào: {input_file}")

    print(f"\n🎬 BẮT ĐẦU CHUYỂN ĐỔI VIDEO 16:9 SANG 9:16")
    print(f"  → Input: {input_file}")
    print(f"  → Output: {output_file}")

    start_time = time.time()
    total_duration = _get_video_duration(input_file)

    # 1. Cấu hình Encoder & Font theo nền tảng
    encoder_opts = []
    if platform.lower() == "windows":
        font_path = "C\\:/Windows/Fonts/arial.ttf"
        if use_gpu:
            # Ưu tiên nvenc (NVIDIA). Nếu AMD thì đổi thành: ["-c:v", "h264_amf", "-quality", "quality"]
            encoder_opts = ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "23"]
            print("  → Encoder: h264_nvenc (GPU Windows)")
        else:
            encoder_opts = ["-c:v", "libx264", "-preset", "fast", "-crf", "23"]
            print("  → Encoder: libx264 (CPU Windows)")
    elif platform.lower() == "macos":
        font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
        if use_gpu:
            encoder_opts = ["-c:v", "h264_videotoolbox", "-b:v", "8M"]
            print("  → Encoder: h264_videotoolbox (GPU macOS)")
        else:
            encoder_opts = ["-c:v", "libx264", "-preset", "fast", "-crf", "23"]
            print("  → Encoder: libx264 (CPU macOS)")
    else:
        # Linux (vd: Kaggle, WSL)
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if not os.path.exists(font_path):
            font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        if use_gpu:
            encoder_opts = ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "23"]
            print("  → Encoder: h264_nvenc (GPU Linux)")
        else:
            encoder_opts = ["-c:v", "libx264", "-preset", "fast", "-crf", "23"]
            print("  → Encoder: libx264 (CPU Linux)")

    # 2. Tính toán kích thước (Mục tiêu 1080x1920)
    target_w, target_h = 1080, 1920
    video_h = 608  # Chiều cao tỷ lệ của video 16:9 khi width = 1080
    pad_h = (target_h - video_h) // 2

    # 3. Xây dựng Filter Complex cho FFmpeg
    # - Tách video làm 2 luồng: main (giữ nguyên) và temp (dùng làm blur)
    # - temp được lấy frame đầu, loop vô hạn, sau đó blur đi, rồi cắt làm 2 nửa trên/dưới.
    # - Cuối cùng ghép (vstack) 3 phần: nửa trên (blur), main, nửa dưới (blur)
    # - Chèn text lên vùng blur
    blur_radius = 25
    blur_power = 1

    filter_complex = (
        f"[0:v]split=2[main][temp];"
        f"[temp]trim=start_frame=0:end_frame=1,"
        f"loop=loop=9999:size=1,setpts=PTS-STARTPTS,"
        f"boxblur={blur_radius}:{blur_power},"
        f"split=2[blurred1][blurred2];"
        f"[blurred1]scale={target_w}:{pad_h}:force_original_aspect_ratio=increase,"
        f"crop={target_w}:{pad_h}[tp];"
        f"[blurred2]scale={target_w}:{pad_h}:force_original_aspect_ratio=increase,"
        f"crop={target_w}:{pad_h}[bp];"
        f"[main]scale={target_w}:{video_h}[mid];"
        f"[tp][mid][bp]vstack=inputs=3[combined]"
    )

    caption_configs = caption_configs or {}
    top_text = caption_configs.get("top_text", "")
    bottom_text = caption_configs.get("bottom_text", "")
    out_map = "[combined]"

    if top_text or bottom_text:
        fontcolor = caption_configs.get("fontcolor", "black")
        fontsize = caption_configs.get("fontsize", 70)
        box = caption_configs.get("box", 1)
        boxcolor = caption_configs.get("boxcolor", "white")
        boxborderw = caption_configs.get("boxborderw", 20)

        box_str = (
            f":box={box}:boxcolor={boxcolor}:boxborderw={boxborderw}" if box else ""
        )

        drawtext_filters = []
        if top_text:
            drawtext_filters.append(
                f"drawtext=text='{top_text}':fontcolor={fontcolor}:fontsize={fontsize}{box_str}"
                f":x=(w-text_w)/2:y={pad_h}-text_h-40:fontfile='{font_path}'"
            )
        if bottom_text:
            drawtext_filters.append(
                f"drawtext=text='{bottom_text}':fontcolor={fontcolor}:fontsize={max(10, fontsize-10)}{box_str}"
                f":x=(w-text_w)/2:y=h-{pad_h}+40:fontfile='{font_path}'"
            )
        filter_complex += ";" + "[combined]" + ",".join(drawtext_filters) + "[v]"
        out_map = "[v]"

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_file,
        "-filter_complex",
        filter_complex,
        "-map",
        out_map,
        "-map",
        "0:a?",  # Giữ nguyên audio nếu có
        *encoder_opts,
        "-c:a",
        "copy",
        "-shortest",
        "-movflags",
        "+faststart",
        output_file,
    ]

    # 4. Thực thi và theo dõi tiến trình
    try:
        _run_ffmpeg_with_progress(
            cmd, total_duration=total_duration, label="Render 9:16 Video"
        )
        elapsed = time.time() - start_time
        print(f"🎉 Hoàn thành chuyển đổi! Tổng thời gian chạy: {elapsed:.2f} giây")
        return output_file

    except subprocess.CalledProcessError as e:
        print(f"\n❌ FFmpeg lỗi trong quá trình render (Exit code: {e.returncode})")
        raise
    except Exception as e:
        print(f"\n❌ Đã xảy ra lỗi: {e}")
        raise


# code test
if __name__ == "__main__":
    # Mã chạy thử (Ví dụ minh họa)
    input_test = os.path.join("data", "video", "input", "clip-to-test.mp4")
    output_test = "output_916.mp4"

    # Tạo file video test trống để chạy thử nếu chưa có
    if not os.path.exists(input_test):
        print(
            f"⚠️ Không tìm thấy '{input_test}'. Đang tạo một video 16:9 test mẫu dài 5s..."
        )
        os.makedirs(os.path.dirname(input_test), exist_ok=True)
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc=duration=5:size=1080x608:rate=30",
                "-c:v",
                "libx264",
                input_test,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    try:
        convert_169_to_916(
            input_file=input_test,
            output_file=output_test,
            caption_configs={
                "top_text": "Tiêu đề video (Trên)",
                "bottom_text": "Phụ đề / Call to Action (Dưới)",
                "fontcolor": "black",
                "fontsize": 70,
                "box": 1,
                "boxcolor": "white",
                "boxborderw": 20,
            },
            use_gpu=False,
            platform="windows",
        )
    except Exception as e:
        print("Test thất bại.")
