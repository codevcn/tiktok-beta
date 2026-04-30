(solved)

# TÀI LIỆU NGHIÊN CỨU: Chuyển đổi Video 16:9 → 9:16 bằng FFmpeg & Python

> **Ngày thực hiện:** 2026-04-30
> **Môi trường:** Windows 11 (GPU AMD) + macOS (Apple Silicon M1/M2, VideoToolbox)
> **Mục tiêu:** Chuyển video ngang 16:9 sang dọc 9:16 (1080×1920) theo kiểu "Triple Stack" với ảnh tĩnh mờ ở phần trên và dưới.

---

## 1. Thiết kế ban đầu — Triple Stack Logic

Khung hình dọc 1080×1920 được chia làm 3 phần:

```
┌─────────────────────┐
│   TOP PAD (ảnh mờ)  │  ← Frame đầu video, blur, tĩnh
├─────────────────────┤
│  VIDEO GỐC 16:9     │  ← Giữ nguyên tỷ lệ, full chất lượng
├─────────────────────┤
│ BOTTOM PAD (ảnh mờ) │  ← Frame đầu video, blur, tĩnh
└─────────────────────┘
```

| Thành phần | Kích thước | Nội dung                |
| ---------- | ---------- | ----------------------- |
| Top Pad    | 1080×656   | Frame đầu video, làm mờ |
| Middle     | 1080×608   | Video gốc giữ tỷ lệ     |
| Bottom Pad | 1080×656   | Frame đầu video, làm mờ |

---

## 2. Lỗi #1 — Treo ở 99% (Cả Windows & macOS)

### Triệu chứng

```
Tiến trình: 99.0% | 98.50s / 99.31s
[chương trình treo, không thoát]
```

### Phân tích nguyên nhân

| #   | Nguyên nhân                       | Giải thích                                                                   |
| --- | --------------------------------- | ---------------------------------------------------------------------------- |
| A   | `loop=-1` không có điểm dừng      | FFmpeg không biết điểm kết thúc, `-shortest` đôi khi không cắt được đúng lúc |
| B   | `readline()` deadlock pipe buffer | Python không đọc kịp stderr → buffer đầy → cả 2 tiến trình chờ nhau          |
| C   | Hardware encoder latency          | AMF/VideoToolbox giữ frame cuối trong GPU buffer, không báo qua `time=...`   |

### Fix áp dụng

**Fix A — Đổi `loop=-1` thành `loop=9999`:**

```python
# ❌ Trước
loop=loop=-1:size=1

# ✅ Sau
loop=loop=9999:size=1
```

**Fix B — Dùng thread riêng đọc stderr:**

```python
# ❌ Trước — readline() block khi buffer đầy
while True:
    line = process.stderr.readline()
    ...

# ✅ Sau — thread daemon đọc song song, không bao giờ block main thread
stderr_thread = threading.Thread(
    target=read_stderr,
    args=(process, total_duration),
    daemon=True
)
stderr_thread.start()
```

**Fix C — Timeout động thay vì cứng 60s:**

```python
# ❌ Trước — cứng 60s, video dài hơn là bị kill oan
process.wait(timeout=60)

# ✅ Sau — timeout tính theo độ dài video
dynamic_timeout = total_duration * 3 + 120
process.wait(timeout=dynamic_timeout)
```

---

## 3. Lỗi #2 — Timeout ở 40% (Windows AMD)

### Triệu chứng

```
Tiến trình:  40.9% | 40.58s / 99.31s
⚠️ GPU encoder timeout! Thử lại với CPU (libx264)...
```

### Nguyên nhân

Timeout cứng `60s` quá ngắn so với video `99.31s`. Chương trình kill FFmpeg ngay khi đang chạy bình thường.

### Fix

Áp dụng công thức timeout động (Fix C ở trên):

```
timeout = 99.31 × 3 + 120 = ~418 giây
```

Sau fix, video chạy xuyên suốt đến 100% thành công.

---

## 4. Lỗi #3 — Bottom Pad hiển thị video động thay vì ảnh tĩnh (macOS & Windows)

### Triệu chứng

Phần dưới cùng (Bottom Pad) phát video động giống hệt phần giữa, thay vì ảnh tĩnh mờ như phần trên.

### Nguyên nhân

Trong FFmpeg, **một stream đã được đặt tên không thể dùng 2 lần**. Code cũ dùng `[blurred]` cho cả `[tp]` và `[bp]`:

```python
# ❌ Trước — [blurred] bị dùng 2 lần, lần 2 FFmpeg fallback về stream gốc
[blurred]scale=...crop...[tp];
[blurred]scale=...crop...[bp];   # ← [blurred] đã hết, FFmpeg lấy stream gốc
```

### Fix — Split `[blurred]` thành 2 trước khi dùng:

```python
# ✅ Sau — split thành [blurred1] và [blurred2]
boxblur=50:3,
split=2[blurred1][blurred2];
[blurred1]scale=...crop...[tp];
[blurred2]scale=...crop...[bp];
```

---

## 5. Cải tiến — Thêm điều chỉnh độ mờ

### Vị trí chỉnh trong code

```python
# ============================================
# ĐIỀU CHỈNH ĐỘ MỜ Ở ĐÂY
# boxblur=RADIUS:POWER
# RADIUS: số càng lớn càng mờ (tối đa ~60)
# POWER:  số lần áp dụng blur (thường 1-3)
# ============================================
f"boxblur=50:3,"  # ← CHỈNH SỐ NÀY
```

### Bảng tham khảo

| Mức độ    | Giá trị        | Ghi chú               |
| --------- | -------------- | --------------------- |
| Nhẹ       | `boxblur=15:1` | Nhìn thấy rõ nội dung |
| Vừa       | `boxblur=30:2` | Blur vừa phải         |
| Mờ nhiều  | `boxblur=50:3` | Khuyến nghị           |
| Gần trắng | `boxblur=60:3` | Gần như xóa nội dung  |

---

## 6. Lỗi #4 — Return code 8 trên macOS

### Triệu chứng

```
❌ FFmpeg lỗi! Return code: 8
```

### Vấn đề debug

Return code 8 là lỗi chung của FFmpeg, không đủ thông tin để biết nguyên nhân thực sự.

### Fix — Thêm error logging chi tiết

```python
def read_stderr(process, total_duration):
    error_lines = []
    for line in process.stderr:
        error_lines.append(line)  # ← Gom tất cả output
        ...
    return error_lines

# Khi lỗi, in 20 dòng cuối
if process.returncode != 0:
    print("\n--- FFmpeg Error Log (20 dòng cuối) ---")
    for line in error_log[-20:]:
        print(line, end="")
```

Sau khi thêm logging, lỗi được xác định và giải quyết thành công.

---

## 7. Tổng hợp tất cả thay đổi so với code gốc

| #   | Thay đổi         | File gốc               | File đã sửa                           |
| --- | ---------------- | ---------------------- | ------------------------------------- |
| 1   | Loop ảnh nền     | `loop=-1` (vô tận)     | `loop=9999` (có giới hạn)             |
| 2   | Đọc stderr       | `readline()` tuần tự   | `threading.Thread` song song          |
| 3   | Timeout          | Cứng `60s`             | Động: `total_duration × 3 + 120`      |
| 4   | Dùng stream blur | `[blurred]` dùng 2 lần | `split=2[blurred1][blurred2]`         |
| 5   | Debug            | Không có log lỗi       | In 20 dòng stderr cuối khi lỗi        |
| 6   | Độ mờ            | `boxblur=15:1`         | `boxblur=50:3` (có comment hướng dẫn) |

---

## 8. Code hoàn chỉnh cuối cùng

### Windows (AMD GPU)

```python
import subprocess
import threading
import time
import re
import sys

def read_stderr(process, total_duration):
    time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})")
    error_lines = []
    for line in process.stderr:
        error_lines.append(line)
        match = time_pattern.search(line)
        if match:
            cur_sec = sum(x * f for x, f in zip(map(float, match.groups()), [3600, 60, 1]))
            progress = min((cur_sec / total_duration) * 100, 99.9)
            sys.stdout.write(f"\rTiến trình: {progress:>5.1f}% | {cur_sec:.2f}s / {total_duration:.2f}s")
            sys.stdout.flush()
    return error_lines

def convert_916_windows(input_file, output_file, top_text, bottom_text):
    probe_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', input_file]
    total_duration = float(subprocess.check_output(probe_cmd).strip())
    print(f"📹 Thời lượng video: {total_duration:.2f}s")

    font_path = "C\\:/Windows/Fonts/arial.ttf"
    target_w, target_h = 1080, 1920
    video_h = 608
    pad_h = (target_h - video_h) // 2

    filter_complex = (
        f"[0:v]split=2[main][temp];"
        f"[temp]trim=start_frame=0:end_frame=1,"
        f"loop=loop=9999:size=1,setpts=PTS-STARTPTS,"
        # ============================================
        # ĐIỀU CHỈNH ĐỘ MỜ Ở ĐÂY
        # boxblur=RADIUS:POWER | Nhẹ:15:1 | Vừa:30:2 | Mờ:50:3
        # ============================================
        f"boxblur=50:3,"  # ← CHỈNH SỐ NÀY
        f"split=2[blurred1][blurred2];"
        f"[blurred1]scale={target_w}:{pad_h}:force_original_aspect_ratio=increase,crop={target_w}:{pad_h}[tp];"
        f"[blurred2]scale={target_w}:{pad_h}:force_original_aspect_ratio=increase,crop={target_w}:{pad_h}[bp];"
        f"[main]scale={target_w}:{video_h}[mid];"
        f"[tp][mid][bp]vstack=inputs=3[combined];"
        f"[combined]"
        f"drawtext=text='{top_text}':fontcolor=white:fontsize=70:x=(w-text_w)/2:y=({pad_h}-text_h)/2:fontfile='{font_path}',"
        f"drawtext=text='{bottom_text}':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=h-({pad_h}+text_h)/2:fontfile='{font_path}'[v]"
    )

    cmd = [
        'ffmpeg', '-i', input_file,
        '-filter_complex', filter_complex,
        '-map', '[v]', '-map', '0:a?',
        '-c:v', 'h264_amf', '-rc', 'cqp', '-qp_i', '19', '-qp_p', '19', '-quality', 'quality',
        '-c:a', 'copy', '-shortest', '-movflags', '+faststart',
        output_file, '-y'
    ]

    start_time = time.time()
    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True, encoding='utf-8')

    error_log = []
    stderr_thread = threading.Thread(
        target=lambda: error_log.extend(read_stderr(process, total_duration)), daemon=True)
    stderr_thread.start()

    dynamic_timeout = total_duration * 3 + 120
    try:
        process.wait(timeout=dynamic_timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        print(f"\n⚠️ Timeout sau {dynamic_timeout:.0f}s!")
        return

    stderr_thread.join(timeout=5)
    elapsed = time.time() - start_time

    if process.returncode == 0:
        print(f"\n✅ Hoàn thành! Thời gian: {elapsed:.2f}s")
    else:
        print(f"\n❌ FFmpeg lỗi! Return code: {process.returncode}")
        print("\n--- FFmpeg Error Log (20 dòng cuối) ---")
        for line in error_log[-20:]:
            print(line, end="")

if __name__ == "__main__":
    convert_916_windows("input.mp4", "output_916.mp4", "Tiêu đề trên", "Tiêu đề dưới")
```

### macOS (VideoToolbox)

```python
import subprocess
import threading
import time
import re
import sys

def read_stderr(process, total_duration):
    time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})")
    error_lines = []
    for line in process.stderr:
        error_lines.append(line)
        match = time_pattern.search(line)
        if match:
            cur_sec = sum(x * f for x, f in zip(map(float, match.groups()), [3600, 60, 1]))
            progress = min((cur_sec / total_duration) * 100, 99.9)
            sys.stdout.write(f"\rTiến trình: {progress:>5.1f}% | {cur_sec:.2f}s / {total_duration:.2f}s")
            sys.stdout.flush()
    return error_lines

def convert_916_macos(input_file, output_file, top_text, bottom_text):
    probe_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', input_file]
    total_duration = float(subprocess.check_output(probe_cmd).strip())
    print(f"📹 Thời lượng video: {total_duration:.2f}s")

    font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
    target_w, target_h = 1080, 1920
    video_h = 608
    pad_h = (target_h - video_h) // 2

    filter_complex = (
        f"[0:v]split=2[main][temp];"
        f"[temp]trim=start_frame=0:end_frame=1,"
        f"loop=loop=9999:size=1,setpts=PTS-STARTPTS,"
        # ============================================
        # ĐIỀU CHỈNH ĐỘ MỜ Ở ĐÂY
        # boxblur=RADIUS:POWER | Nhẹ:15:1 | Vừa:30:2 | Mờ:50:3
        # ============================================
        f"boxblur=50:3,"  # ← CHỈNH SỐ NÀY
        f"split=2[blurred1][blurred2];"
        f"[blurred1]scale={target_w}:{pad_h}:force_original_aspect_ratio=increase,crop={target_w}:{pad_h}[tp];"
        f"[blurred2]scale={target_w}:{pad_h}:force_original_aspect_ratio=increase,crop={target_w}:{pad_h}[bp];"
        f"[main]scale={target_w}:{video_h}[mid];"
        f"[tp][mid][bp]vstack=inputs=3[combined];"
        f"[combined]"
        f"drawtext=text='{top_text}':fontcolor=white:fontsize=70:x=(w-text_w)/2:y=({pad_h}-text_h)/2:fontfile='{font_path}',"
        f"drawtext=text='{bottom_text}':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=h-({pad_h}+text_h)/2:fontfile='{font_path}'[v]"
    )

    cmd = [
        'ffmpeg', '-i', input_file,
        '-filter_complex', filter_complex,
        '-map', '[v]', '-map', '0:a?',
        '-c:v', 'h264_videotoolbox', '-b:v', '8M',
        '-c:a', 'copy', '-shortest', '-movflags', '+faststart',
        output_file, '-y'
    ]

    start_time = time.time()
    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True, encoding='utf-8')

    error_log = []
    stderr_thread = threading.Thread(
        target=lambda: error_log.extend(read_stderr(process, total_duration)), daemon=True)
    stderr_thread.start()

    dynamic_timeout = total_duration * 3 + 120
    try:
        process.wait(timeout=dynamic_timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        print(f"\n⚠️ Timeout sau {dynamic_timeout:.0f}s!")
        return

    stderr_thread.join(timeout=5)
    elapsed = time.time() - start_time

    if process.returncode == 0:
        print(f"\n✅ Hoàn thành! Thời gian: {elapsed:.2f}s")
    else:
        print(f"\n❌ FFmpeg lỗi! Return code: {process.returncode}")
        print("\n--- FFmpeg Error Log (20 dòng cuối) ---")
        for line in error_log[-20:]:
            print(line, end="")

if __name__ == "__main__":
    convert_916_macos("input.mp4", "output_916.mp4", "Tiêu đề trên", "Tiêu đề dưới")
```

---

## 9. Bài học rút ra

1. **FFmpeg stream naming:** Mỗi stream `[tên]` chỉ được dùng **đúng 1 lần**. Cần dùng `split` nếu muốn chia sẻ cùng một nguồn cho nhiều nhánh.

2. **Subprocess deadlock:** Không bao giờ dùng `readline()` hoặc `communicate()` kết hợp với `wait()` trên cùng một thread khi pipe buffer có thể đầy. Luôn dùng thread riêng.

3. **Timeout phải động:** Timeout xử lý video phải tỷ lệ với độ dài video. Công thức an toàn: `duration × 3 + 120`.

4. **Hardware encoder flush:** GPU encoder (AMF, VideoToolbox) có latency ở frame cuối — đây là hành vi bình thường, không phải lỗi treo. Cần timeout đủ lớn để chờ flush hoàn tất.

5. **Debug bằng stderr log:** Khi FFmpeg báo lỗi chung (return code ≠ 0), luôn cần xem 20 dòng cuối của stderr để biết nguyên nhân thực sự.
