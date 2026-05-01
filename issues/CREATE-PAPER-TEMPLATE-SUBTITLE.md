# Đặc tả Kỹ thuật: Triển khai Phụ đề Style "Dải giấy" (Paper Strip) bằng Pysubs2

## 1. Tổng quan nhu cầu

Mục tiêu là tích hợp tính năng tạo đồ họa văn bản tự động vào dự án **TikTok-Beta** [User Summary]. Phong cách phụ đề này mô phỏng các dải giấy được dán lên video, một xu hướng phổ biến trong các nội dung ngắn để tăng tỷ lệ giữ chân người xem.

### Yêu cầu về thị giác:

- **Màu sắc**: Chữ đen (Primary Color) trên nền trắng hoàn toàn (Opaque Box).
- **Hình dạng**: Hộp nền hình chữ nhật bao quanh văn bản với khoảng cách lề (padding) cân đối.
- **Vị trí**:
  - **Header**: Cố định ở phần trên để đặt tiêu đề thu hút.
  - **Part Label**: Cố định ở phần dưới để đánh dấu phân đoạn (ví dụ: Part 1, Part 2).

---

## 2. Giải pháp Kỹ thuật: Pysubs2 & ASS Format

Thay vì sử dụng các thư viện xử lý ảnh (Image-based), chúng ta sử dụng **pysubs2** để tạo tệp phụ đề **Advanced SubStation Alpha (.ass)**[cite: 2].

### Tại sao đây là cách tối ưu trên máy Local?

1.  **Tốc độ Render**: Tận dụng thư viện `libass` của FFmpeg giúp việc "burn" sub diễn ra cực nhanh so với việc ghép lớp ảnh (overlaying)[cite: 2].
2.  **Độ sắc nét**: Phụ đề dạng vector (ASS) giữ nguyên độ sắc nét ở mọi độ phân giải video (720p, 1080p, 4K).
3.  **Dễ dàng tự động hóa**: Có thể điều chỉnh nội dung qua file cấu hình `flow-inputs.json` mà không cần can thiệp vào mã nguồn xử lý hình ảnh[cite: 2].

---

## 3. Cấu hình Style chi tiết (Technical Specs)

Để đạt được hiệu ứng "Dải giấy" chuẩn xác, cấu hình `SSAStyle` trong `pysubs2` cần được thiết lập như sau:

| Thuộc tính         | Giá trị                 | Mục đích                                                    |
| :----------------- | :---------------------- | :---------------------------------------------------------- |
| **`BorderStyle`**  | `3`                     | Chế độ Opaque Box (Tạo hộp nền đặc thay vì viền chữ).       |
| **`Outline`**      | `3.0` đến `5.0`         | Quyết định độ rộng của "lề" trắng (Padding) xung quanh chữ. |
| **`PrimaryColor`** | `&H000000`              | Màu chữ đen thuần túy.                                      |
| **`BackColor`**    | `&HFFFFFF`              | Màu trắng của dải giấy làm nền.                             |
| **`Alignment`**    | `8` (Trên) / `2` (Dưới) | Xác định vị trí neo của dải giấy trên khung hình.           |
| **`MarginV`**      | `40` - `60`             | Khoảng cách an toàn từ mép video đến dải giấy.              |

---

## 4. Hướng dẫn Triển khai Code

### Cấu trúc thư mục đề xuất:

Dựa trên cấu trúc hiện tại của dự án[cite: 2]:

- `src/features/generate_stickers.py`: Module tạo file ASS.
- `src/utils/helpers.py`: Các hàm bổ trợ về màu sắc và cấu hình.

### Mã nguồn mẫu:

```python
import pysubs2

def create_paper_strip_sub(top_text, part_text, output_path):
    subs = pysubs2.SSAFile()

    # Tạo Style cho dải giấy phía trên
    style_top = pysubs2.SSAStyle(
        fontname="Arial Rounded MT Bold", fontsize=28, bold=True,
        primarycolor=pysubs2.Color(0, 0, 0),    # Chữ đen
        backcolor=pysubs2.Color(255, 255, 255), # Nền trắng
        borderstyle=3, outline=4, alignment=8, marginv=45
    )

    # Tạo Style cho nhãn Part phía dưới
    style_part = style_top.copy()
    style_part.alignment = 2
    style_part.marginv = 60
    style_part.fontsize = 22

    subs.styles["TopStrip"] = style_top
    subs.styles["PartStrip"] = style_part

    # Thêm sự kiện vào dòng thời gian (hiển thị toàn bộ video)
    if top_text:
        event_top = pysubs2.SSAEvent(start=0, end=pysubs2.make_time(m=10), text=top_text)
        event_top.style = "TopStrip"
        subs.append(event_top)

    if part_text:
        event_part = pysubs2.SSAEvent(start=0, end=pysubs2.make_time(m=10), text=part_text)
        event_part.style = "PartStrip"
        subs.append(event_part)

    subs.save(output_path)
```

---

## 5. Quy trình thực thi (Workflow)

Để chạy dự án trên máy local một cách chuyên nghiệp:

1.  **Cấu hình**: Cập nhật nội dung tiêu đề và số Part vào `data/video/input/flow-inputs.json`[cite: 2].
2.  **Khởi tạo ASS**: Chạy script để tạo tệp `.ass` tạm thời chứa các dải giấy.
3.  **Xử lý Video**: Sử dụng `subprocess` để gọi FFmpeg tích hợp phụ đề vào video gốc[cite: 2].
    ```bash
    ffmpeg -i input.mp4 -vf "subtitles=paper_strips.ass" -c:a copy output.mp4
    ```
4.  **Kiểm tra**: Kết quả sẽ được lưu vào thư mục `data/video/output` theo cấu trúc phân loại của dự án[cite: 2].

---

## 6. Lưu ý về Font chữ

Trên máy cục bộ (Windows/macOS), hãy đảm bảo tên `fontname` trong code trùng khớp chính xác với tên font đã cài đặt trong hệ thống để FFmpeg có thể nhận diện và render đúng style. Các font khuyên dùng: _Arial Rounded MT Bold, Montserrat, Be Vietnam Pro_.

```

```
