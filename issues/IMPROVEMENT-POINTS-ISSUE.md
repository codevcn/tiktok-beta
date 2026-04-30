# Improvement Points Issue

## Bối cảnh

Sau khi đọc toàn bộ source trong `src`, pipeline hiện tại đã có luồng chính khá rõ:

`download video -> remove watermark -> extract audio -> transcribe -> fix typo -> translate optional -> burn subtitle`

Code đã xử lý được nhiều vấn đề thực tế như retry AI, fallback provider, GPU subprocess cho Whisper và progress khi chạy FFmpeg. Tuy vậy vẫn còn một số điểm có thể cải thiện để pipeline ổn định hơn, dễ debug hơn và dễ mở rộng hơn.

## Các điểm có thể cải thiện

### 1. Thêm bước validate SRT sau khi AI sửa typo hoặc dịch (completed)

Hiện tại `fix_transcribe_typos.py` và `translate_srt.py` gửi toàn bộ SRT cho AI rồi ghi kết quả trực tiếp ra file.

Rủi ro:

- AI có thể đổi số thứ tự subtitle.
- AI có thể đổi timestamp.
- AI có thể merge/split block.
- AI có thể thêm text ngoài SRT hoặc làm sai format.

Đề xuất:

- Parse SRT đầu vào và đầu ra sau mỗi bước AI.
- Kiểm tra số block, index, timestamp có giữ nguyên không.
- Nếu output sai format, retry với prompt sửa lỗi hoặc fallback về bản trước đó.
- Log rõ block nào bị lệch.

Ưu tiên: Cao.

### 2. Cải thiện vấn đề dấu câu trong transcript (completed)

Issue hiện tại: `PUNCTUATION-MARKS-ISSUE.md`.

Hiện prompt sửa typo có nhắc "obvious punctuation and spacing mistakes", nhưng chưa có bước/chế độ riêng để yêu cầu AI thêm dấu câu tự nhiên cho transcript.

Đề xuất:

- Tách rõ mục tiêu "fix transcription typo" và "restore punctuation".
- Thêm rule yêu cầu giữ nguyên block/timestamp nhưng được phép thêm dấu câu trong text.
- Có thể thêm config như:

Ưu tiên: Cao.

### 3. `parallel_execution` có trong config nhưng chưa được triển khai

Trong `flow-inputs.json` có field `parallel_execution`, doc cũng mô tả chức năng này, nhưng `auto_burn_sub_to_video.py` hiện vẫn xử lý tuần tự.

Rủi ro:

- Người dùng bật `parallel_execution: true` nhưng hành vi không thay đổi.
- Config và code bị lệch nhau.

Đề xuất:

- Hoặc triển khai xử lý nhiều link song song.
- Hoặc tạm thời validate và log rằng field này chưa được hỗ trợ.
- Nếu triển khai song song, cần giới hạn concurrency vì GPU, FFmpeg và API AI đều là tài nguyên nặng.

Ưu tiên: Thấp (Triển khai sau).

### 4. Burn subtitle chưa tận dụng GPU encode

`remove_watermark.py` có hỗ trợ `h264_nvenc` khi `use_gpu=true`, nhưng `burn_ass_subtitle.py` luôn dùng `libx264`.

Rủi ro:

- Bước burn subtitle có thể chậm dù người dùng đã bật GPU.
- Config `use_gpu` chưa nhất quán giữa các bước encode video.

Đề xuất:

- Truyền `use_gpu` vào `burn_subtitle_to_video`.
- Nếu bật GPU, dùng `h264_nvenc` với preset/CQ phù hợp.
- Nếu FFmpeg không hỗ trợ NVENC, fallback CPU và log rõ.

Ưu tiên: Trung bình.

### 5. Cần kiểm tra dependency hệ thống trước khi chạy pipeline

Pipeline phụ thuộc vào:

- `ffmpeg`
- filter FFmpeg `delogo`
- filter FFmpeg `ass` hoặc `subtitles`
- `yt-dlp`
- Python packages trong `requirements.txt`
- API key `GOOGLE_API_KEY` hoặc `OPENAI_API_KEY`

Hiện lỗi thường chỉ xuất hiện khi pipeline đã chạy tới bước tương ứng.

Đề xuất:

- Thêm bước preflight check ở đầu pipeline.
- Kiểm tra command tồn tại và version.
- Kiểm tra FFmpeg có filter cần thiết.
- Kiểm tra ít nhất một API key khả dụng trước khi tới bước AI.
- In báo cáo ngắn trước khi xử lý video.

Ưu tiên: Cao.

### 6. Chia nhỏ prompt và xử lý SRT dài theo chunk an toàn

Hiện AI nhận toàn bộ SRT trong một request.

Rủi ro:

- Video dài có thể vượt context/token limit.
- Request lớn dễ fail hoặc tốn chi phí.
- Nếu fail, phải chạy lại toàn bộ SRT.

Đề xuất:

- Parse SRT thành block.
- Chia chunk theo số block hoặc số ký tự.
- Mỗi chunk vẫn giữ index/timestamp.
- Ghép output và validate toàn file sau cùng.

Ưu tiên: Trung bình.

### 7. Chuẩn hóa config schema cho `flow-inputs.json`

Hiện config được đọc trực tiếp bằng `json.load`, validation mới có trong `scripts/edit_flow_inputs.py`, chưa nằm trong pipeline chính.

Rủi ro:

- Config sai chỉ phát hiện muộn khi pipeline đang chạy.
- Dễ thiếu field hoặc sai kiểu dữ liệu.

Đề xuất:

- Tạo module validate config dùng chung.
- Reuse validation trong cả `scripts/edit_flow_inputs.py` và pipeline.
- Validate:
  - `links` non-empty
  - `link` bắt buộc
  - `flows` hợp lệ
  - `subtitle_configs` đúng kiểu
  - `watermark` đủ `x1`, `y1`, `x2`, `y2` nếu có
  - `original_lang_code` và `target_lang_code` theo ISO 639-1 nếu cần

Ưu tiên: Cao.

### 9. Cải thiện quản lý file trung gian và resume pipeline

Hiện mỗi lần chạy tạo thư mục output timestamp mới và chạy lại từ đầu.

Rủi ro:

- Nếu fail ở bước cuối, phải chạy lại download/transcribe/AI.
- Tốn thời gian và API cost.

Đề xuất:

- Thêm manifest trạng thái trong output dir, ví dụ `pipeline-state.json`.
- Nếu file trung gian đã tồn tại và hợp lệ, cho phép skip bước đã xong.
- Có option `resume_from_output_dir`.
- Có option giữ/xóa file trung gian.

Ưu tiên: Thấp (Triển khai sau).

### 12. Tách domain logic khỏi CLI/log side effects

Nhiều function vừa xử lý logic, vừa print, vừa gọi subprocess.

Đề xuất:

- Giữ public function đơn giản, nhưng tách phần build command thành helper riêng.
- Dễ unit test các command FFmpeg/yt-dlp mà không cần chạy thật.
- Dễ thêm dry-run/debug mode.

Ưu tiên: Thấp.

## Đề xuất thứ tự xử lý

1. Chuẩn hóa config schema cho `flow-inputs.json` và dùng chung validation giữa `scripts/edit_flow_inputs.py` với pipeline chính.
2. Thêm preflight check dependency trước khi xử lý video để phát hiện sớm lỗi `ffmpeg`, filter cần thiết, `yt-dlp`, package Python và API key.
3. Thêm validation SRT sau các bước AI sửa typo hoặc dịch để đảm bảo index, timestamp và số block không bị thay đổi.
4. Cải thiện prompt/bước hậu xử lý dấu câu trong transcript, dựa trên validation SRT để không phá cấu trúc phụ đề.
5. Hỗ trợ GPU encode cho bước burn subtitle, có fallback CPU nếu FFmpeg/NVENC không khả dụng.
6. Chia nhỏ SRT dài thành chunk an toàn khi gọi AI, rồi ghép lại và validate toàn bộ kết quả.
7. Xử lý rõ `parallel_execution`: hoặc triển khai với giới hạn concurrency, hoặc cảnh báo rằng field này chưa được hỗ trợ.
8. Bổ sung cơ chế quản lý file trung gian/resume pipeline để giảm việc chạy lại từ đầu khi lỗi ở bước sau.
9. Tách dần domain logic khỏi phần CLI/print/subprocess để code dễ test và dễ mở rộng hơn.

## Tiêu chí hoàn thành tổng quát

- Config sai được phát hiện trước khi pipeline bắt đầu download hoặc xử lý video.
- Môi trường chạy được kiểm tra sớm, gồm `ffmpeg`, filter FFmpeg cần thiết, `yt-dlp`, dependency Python và API key.
- Output từ AI luôn được kiểm tra định dạng SRT trước khi dùng cho bước tiếp theo.
- Bước sửa typo/dấu câu chỉ thay đổi nội dung text, không làm đổi index, timestamp, số block hoặc thứ tự subtitle.
- Pipeline xử lý nhất quán với config `use_gpu`, đặc biệt ở các bước encode video có thể tận dụng GPU.
- Với SRT dài, pipeline không phụ thuộc vào một request AI duy nhất và vẫn ghép được kết quả hợp lệ.
- Các field config chưa được hỗ trợ đầy đủ, như `parallel_execution`, phải có hành vi rõ ràng: chạy đúng hoặc cảnh báo rõ.
- Khi pipeline fail ở bước giữa hoặc bước cuối, người dùng có đường hướng để resume/skip bước đã hoàn thành thay vì luôn chạy lại từ đầu.
