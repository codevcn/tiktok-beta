"""
Tiện ích dùng chung cho các feature module.
"""

import os
import re
import shutil
import subprocess
from urllib.parse import urlparse, parse_qs
import json


def run_ffmpeg_with_progress(command: list, label: str = "Đang xử lý") -> None:
    """
    Chạy lệnh ffmpeg và hiển thị tiến trình % theo thời gian video.
    Parse Duration và time= từ stderr của ffmpeg (đọc theo chunk để xử lý \\r).

    Raises:
        subprocess.CalledProcessError: nếu ffmpeg thoát với exit code != 0.
    """
    process = subprocess.Popen(
        command,
        stderr=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
    )

    duration_secs: float | None = None
    last_pct = -1
    stderr_lines: list[str] = []
    line_buf = b""

    # Kiểm tra an toàn để tránh lỗi NoneType
    if process.stderr is None:
        raise RuntimeError("Không thể khởi tạo luồng stderr từ FFmpeg.")

    for chunk in iter(lambda: process.stderr.read(256), b""):
        line_buf += chunk
        # Tách các dòng bằng \r hoặc \n (ffmpeg dùng \r cho progress)
        parts = re.split(rb"\r|\n", line_buf)
        line_buf = parts[-1]  # phần chưa hoàn chỉnh

        for raw in parts[:-1]:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            stderr_lines.append(line)

            # Parse Duration (1 lần duy nhất)
            if duration_secs is None:
                m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", line)
                if m:
                    h, mn, s = m.groups()
                    duration_secs = int(h) * 3600 + int(mn) * 60 + float(s)

            # Parse time= để tính %
            tm = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
            if tm and duration_secs and duration_secs > 0:
                h, mn, s = tm.groups()
                current = int(h) * 3600 + int(mn) * 60 + float(s)
                pct = min(int(current / duration_secs * 100), 99)
                if pct != last_pct:
                    # Thông tin bổ sung
                    fps_m = re.search(r"fps=\s*([\d.]+)", line)
                    speed_m = re.search(r"speed=\s*([\d.x]+)", line)
                    size_m = re.search(r"size=\s*(\S+)", line)
                    extra = ""
                    if fps_m and float(fps_m.group(1)) > 0:
                        extra += f"  fps={fps_m.group(1)}"
                    if speed_m:
                        extra += f"  speed={speed_m.group(1)}"
                    if size_m:
                        extra += f"  size={size_m.group(1)}"
                    print(f"\r  ⏳ {label}: {pct:3d}%{extra}    ", end="", flush=True)
                    last_pct = pct

    process.wait()

    if process.returncode != 0:
        print()  # xuống dòng sau progress bar
        raise subprocess.CalledProcessError(
            process.returncode,
            command,
            stderr="\n".join(stderr_lines[-30:]),
        )

    print(f"\r  ✅ {label}: 100%                                    ")


def download_video(link: str, output_dir: str) -> str:
    """
    Tải video từ URL bằng yt-dlp + aria2c ở chất lượng 720p, lưu vào output_dir.
    Để yt-dlp/aria2c tự in progress (%, speed, ETA) ra terminal.
    Sau khi tải xong, scan thư mục để lấy đường dẫn file video.

    Format ưu tiên:
      1. Video <=720p (mp4) + audio (m4a) riêng rồi merge
      2. File tổng hợp sẵn (mp4) tối đa 720p
      3. aria2c tải song song nhiều connection để tăng tốc download
    """
    print(f"📥 Đang tải video (720p, aria2c) từ: {link}")

    print("  -> Downloader: aria2c (-N 4, -x 8, -s 8, -k 1M), impersonate chrome")

    if shutil.which("aria2c") is None:
        raise FileNotFoundError(
            "Khong tim thay aria2c trong PATH. "
            "Hay cai aria2/aria2c truoc khi chay download nhanh "
            "(Windows: winget install aria2.aria2 hoac choco install aria2; "
            "macOS: brew install aria2)."
        )

    output_template = os.path.join(output_dir, "%(id)s.%(ext)s")

    command = [
        "yt-dlp",
        "--no-playlist",
        "-N",
        "4",
        "--downloader",
        "aria2c",
        "--downloader-args",
        "aria2c:-x 8 -s 8 -k 1M",
        "--impersonate",
        "chrome",
        "-f",
        (
            "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]"
            "/best[height<=720]"
        ),
        "-o",
        output_template,
        link,
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError:
        print("❌ yt-dlp báo lỗi khi tải video.")
        raise

    video_exts = (".mp4", ".mkv", ".webm", ".avi", ".mov", ".m4v")
    for fname in os.listdir(output_dir):
        if fname.lower().endswith(video_exts):
            fpath = os.path.join(output_dir, fname)
            print(f"✅ Tải xong: {fpath}")
            return fpath

    raise FileNotFoundError(
        f"Không tìm thấy file video nào trong {output_dir} sau khi tải."
    )


def extract_video_id(link: str) -> str:
    """
    Trích xuất video ID từ URL. Hỗ trợ:
      - youtube.com/watch?v=ID
      - youtu.be/ID
      - TikTok và các URL khác: dùng phần cuối path
    """
    parsed = urlparse(link)
    host = parsed.netloc.lower()

    if "youtube.com" in host:
        qs = parse_qs(parsed.query)
        vid = qs.get("v", [None])[0]
        if vid:
            return vid

    if "youtu.be" in host:
        vid = parsed.path.lstrip("/").split("/")[0]
        if vid:
            return vid

    # Fallback: lấy phần cuối path, loại bỏ ký tự không hợp lệ trong tên file
    path_part = parsed.path.rstrip("/").split("/")[-1] or "unknown"
    safe = "".join(c for c in path_part if c.isalnum() or c in "-_")[:30]
    return safe or "unknown"


def load_env(env_path: str = ".env") -> None:
    """Đọc file .env bằng tay, không cần python-dotenv."""
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip("\"'")


def load_links_config(links_json_path: str) -> dict:
    """Đọc và parse file links.json."""
    if not os.path.exists(links_json_path):
        raise FileNotFoundError(f"Không tìm thấy file cấu hình: {links_json_path}")
    with open(links_json_path, "r", encoding="utf-8") as f:
        return json.load(f)
