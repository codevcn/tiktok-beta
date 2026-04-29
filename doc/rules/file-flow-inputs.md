- **Mô tả:**

File này chứa cấu hình đầu vào cho công cụ xử lý video. Nó xác định chế độ xử lý song song, cấu hình sử dụng GPU, danh sách các liên kết video cần xử lý, ngôn ngữ đích cho phụ đề dịch, cấu hình hiển thị phụ đề, vùng xóa watermark, và quy trình (flow) nào sẽ được chạy. Chương trình sẽ đọc file này thay vì yêu cầu người dùng chọn quy trình qua terminal.

- **Ví dụ:**

```json
{
  "parallel_execution": false,
  "use_gpu": false,
  "links": [
    {
      "link": "https://youtu.be/70XSafYpaAA?si=mNl28BE6PeAafe7b",
      "original_lang_code": "ja",
      "target_lang_code": "vi",
      "subtitle_configs": {
        "fontname": "Arial",
        "fontsize": 24,
        "primarycolor": "255,255,0",
        "outlinecolor": "0,0,0",
        "backcolor": "0,0,0,128",
        "outline": 2.0,
        "shadow": 1.0,
        "bold": true,
        "alignment": "BOTTOM_CENTER",
        "marginv": 20,
        "marginl": 0,
        "marginr": 0
      },
      "watermark": {
        "x1": 1111,
        "y1": 3,
        "x2": 1273,
        "y2": 164
      }
    }
  ],
  "flows": {
    "auto_burn_sub_to_video_with_translate": true,
    "auto_burn_sub_to_video_no_translate": false
  }
}
```

- **Giải thích các trường:**
  - `parallel_execution`: Bật (`true`) để công cụ xử lý tất cả các link trong mảng "links" cùng lúc (song song), hoặc tắt (`false`) để xử lý tuần tự từng video một.
  - `use_gpu`: Bật (`true`) để sử dụng GPU (NVIDIA) cho việc transcribe âm thanh (Whisper) và encode video (NVENC), hoặc `false` để sử dụng CPU.
  - `links`: Mảng chứa danh sách cấu hình của các video cần xử lý.
    - `link`: Đường dẫn URL tới video (YouTube, TikTok,...).
    - `original_lang_code`: (Tùy chọn) Mã ngôn ngữ gốc của video theo chuẩn ISO 639-1 (vd: "ja", "en"). Nếu không cung cấp, Whisper sẽ tự động nhận diện.
    - `target_lang_code`: Mã ngôn ngữ đích cho phụ đề dịch theo chuẩn ISO 639-1 (vd: "vi").
    - `subtitle_configs`: Đối tượng chứa cấu hình hiển thị cho phụ đề (chuyển đổi từ SRT sang ASS).
      - `fontname`: Tên font chữ (vd: "Arial").
      - `fontsize`: Kích thước font chữ.
      - `primarycolor`: Màu chính của chữ theo định dạng RGB (vd: "255,255,0" là màu vàng).
      - `outlinecolor`: Màu viền chữ theo định dạng RGB (vd: "0,0,0" là màu đen).
      - `backcolor`: Màu nền của chữ theo định dạng RGBA (vd: "0,0,0,128" là màu đen với độ trong suốt 50%).
      - `outline`: Độ dày của viền chữ.
      - `shadow`: Độ mờ bóng đổ của chữ.
      - `bold`: Cài đặt chữ in đậm (`true` / `false`).
      - `alignment`: Vị trí căn chỉnh phụ đề (vd: "BOTTOM_CENTER").
      - `marginv`: Khoảng cách lề dọc (từ dưới lên).
      - `marginl`: Khoảng cách lề trái.
      - `marginr`: Khoảng cách lề phải.
    - `watermark`: (Tùy chọn) Đối tượng chứa cấu hình xóa watermark trên video.
      - `x1`: Tọa độ X góc trên cùng bên trái của logo/watermark.
      - `y1`: Tọa độ Y góc trên cùng bên trái.
      - `x2`: Tọa độ X góc dưới cùng bên phải.
      - `y2`: Tọa độ Y góc dưới cùng bên phải.
  - `flows`: Đối tượng chỉ định quy trình nào sẽ được kích hoạt khi chạy chương trình.
    - `auto_burn_sub_to_video_with_translate`: Kích hoạt quy trình xử lý đầy đủ bao gồm việc dịch thuật (`true`/`false`).
    - `auto_burn_sub_to_video_no_translate`: Kích hoạt quy trình xử lý phụ đề mà KHÔNG dịch thuật (`true`/`false`).
