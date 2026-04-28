Nhìn theo code hiện tại, chỉ có 1 feature thực sự có tiềm năng tăng tốc GPU rất đáng kể là `transcribe_audio_file.py`; 2 feature video dùng `ffmpeg` cũng có thể đẩy một phần sang GPU; còn các feature gọi Gemini hoặc xử lý text/file thì hầu như không liên quan GPU cục bộ.

**Đánh giá nhanh**

- `transcribe_audio_file.py`: `Rất cao`
- `remove_watermark.py`: `Trung bình`
- `burn_ass_subtitle.py`: `Trung bình đến thấp`
- `extract_audio_from_video.py`: `Rất thấp`
- `fix_transcribe_typos.py`: `Không áp dụng`
- `translate_srt.py`: `Không áp dụng`
- `utils.py/download_video/load_env/load_links_config`: `Không áp dụng`
