Đề xuất giải pháp kỹ thuật dành cho AI Coding. Tài liệu này tập trung vào việc mô tả kiến trúc và logic xử lý để công cụ AI tự thực hiện mã hóa dựa trên ngữ cảnh dự án.

---

# Tài liệu Đặc tả Kỹ thuật: Hệ thống Retry & Chuyển đổi Mô hình (Switcher) cho Pipeline Subtitle

## 1. Phân tích vấn đề (Problem Analysis)

Pipeline hiện tại đang gặp lỗi dừng đột ngột khi gọi API Gemini do trạng thái `503 UNAVAILABLE` (High Demand). Vì hệ thống xử lý video tuần tự, lỗi này làm gián đoạn toàn bộ các bước sau như dịch thuật và chèn phụ đề. Yêu cầu đặt ra là xây dựng một hệ thống có khả năng tự phục hồi và linh hoạt thay đổi nguồn tài nguyên AI khi gặp sự cố.

## 2. Chiến lược xử lý: Multi-Tier Failover Switcher

Thay vì chỉ dừng lại ở việc thử lại trên một model duy nhất, chúng ta sẽ triển khai cơ chế chuyển đổi theo tầng (Tier) để đảm bảo tối đa khả năng thành công của yêu cầu.

### Tầng 1: Mô hình chính (Gemini Pro) + Exponential Backoff

- **Mục tiêu:** Ưu tiên sử dụng mô hình có chất lượng cao nhất hiện có.
- **Kỹ thuật:** Sử dụng thư viện `tenacity` để bọc hàm gọi API.
- **Cấu hình Retry:** Thực hiện kỹ thuật "Exponential Backoff" (chờ tăng dần theo cấp số nhân) để tránh làm quá tải hệ thống trong lúc đang xảy ra "spike" lưu lượng.
- **Điều kiện thử lại:** Chỉ thực hiện khi bắt được các lỗi liên quan đến dịch vụ không sẵn sàng (`503`) hoặc quá giới hạn yêu cầu (`429`).

### Tầng 2: Mô hình dự phòng nội bộ (Gemini Flash)

- **Mục tiêu:** Khi Tầng 1 thất bại hoàn toàn sau số lần thử quy định, hệ thống tự động hạ cấp xuống mô hình thấp hơn nhưng ổn định hơn và có giới hạn băng thông rộng hơn (ví dụ: chuyển từ Gemini 1.5 Pro sang Gemini 1.5 Flash).
- **Kỹ thuật:** Tiếp tục áp dụng `tenacity` với số lần thử ít hơn để kiểm tra tính sẵn sàng của mô hình dự phòng.

### Tầng 3: Nhà cung cấp dự phòng bên ngoài (OpenAI)

- **Mục tiêu:** Đảm bảo pipeline không bị tắc nghẽn nếu toàn bộ hệ thống của Google (Gemini) gặp sự cố kéo dài.
- **Kỹ thuật:** Chuyển đổi hoàn toàn Provider sang OpenAI (sử dụng GPT-4o hoặc GPT-4o-mini). Đây là lớp bảo vệ cuối cùng trước khi báo lỗi video đó thất bại.

---

## 3. Yêu cầu triển khai chi tiết cho AI Coding

### A. Cấu trúc Logic Wrapper

AI cần viết một hàm bao (wrapper) linh hoạt có khả năng nhận danh sách cấu hình mô hình (Model Configurations). Hàm này sẽ:

1. Duyệt qua danh sách các "Tier" đã định nghĩa.
2. Thực hiện gọi API bên trong một khối xử lý được cấu hình bởi `tenacity`.
3. Nếu tất cả các lần thử lại ở một Tier thất bại, bắt ngoại lệ và chuyển sang Tier tiếp theo.
4. Chỉ ném ra lỗi cuối cùng (Final Exception) khi tất cả các Tier đều không thể phản hồi thành công.

### B. Cấu hình Tenacity (Exponential Backoff)

Yêu cầu AI áp dụng các tham số sau cho mỗi lần gọi API:

- **Wait Strategy:** Chờ theo cấp số nhân (ví dụ: bắt đầu từ 2 giây, tối đa 30-60 giây).
- **Stop Strategy:** Dừng lại sau một số lần thử nhất định (ví dụ: 3-5 lần cho mô hình chính, 2-3 lần cho mô hình dự phòng).
- **Retry Predicate:** Chỉ thử lại với các mã lỗi HTTP cụ thể (503, 429). Không thử lại với các lỗi 400 (Bad Request) hoặc 401 (Unauthorized) để tránh lãng phí thời gian.

### C. Quản lý trạng thái Provider

AI cần đảm bảo rằng:

- Mã nguồn có khả năng nhận diện API Key tương ứng với từng nhà cung cấp (Gemini hoặc OpenAI).
- Prompt gửi đi được điều chỉnh định dạng (nếu cần thiết) để tương thích với cấu trúc của từng Provider khác nhau mà vẫn giữ nguyên yêu cầu sửa lỗi chính tả hoặc dịch thuật.

---

## 4. Tiêu chí nghiệm thu (Acceptance Criteria)

1. **Tính bền bỉ:** Khi gặp lỗi `503`, chương trình không được dừng ngay mà phải thực hiện chờ ít nhất 2 lần trước khi quyết định đổi model.
2. **Tính linh hoạt:** Nếu Gemini Pro lỗi, hệ thống phải tự động gọi được Gemini Flash. Nếu vẫn lỗi, phải gọi được OpenAI.
3. **Tính sạch sẽ:** Sử dụng Decorator của `tenacity` để tách biệt logic retry khỏi logic gọi API chính, giữ cho mã nguồn dễ bảo trì.
4. **Thông báo:** Hệ thống phải log rõ ràng trạng thái: "Đang thử lại lần n...", "Đang chuyển sang mô hình dự phòng...", "Đang chuyển sang OpenAI...".
