import os

# --- BẮT ĐẦU ÉP ĐƯỜNG DẪN DLL VÀO HỆ THỐNG ---
venv_path = os.path.join(os.getcwd(), ".venv", "Lib", "site-packages")
cublas_bin = os.path.join(venv_path, "nvidia", "cublas", "bin")
cudnn_bin = os.path.join(venv_path, "nvidia", "cudnn", "bin")
os.environ["PATH"] = f"{cublas_bin};{cudnn_bin};" + os.environ.get("PATH", "")
# ------------------------------------------------

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from faster_whisper import WhisperModel


def format_time_srt(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def transcribe_audio(audio_path: str, srt_output_path: str) -> str:
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Không tìm thấy file: {audio_path}")

    print("  → Đang tải model Whisper large-v3 (CPU / int8)...")
    model = WhisperModel("large-v3", device="cpu", compute_type="int8")

    print("  → Đang phân tích âm thanh...\n")
    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        language="vi",
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    total_duration = info.duration  # giây, dùng để tính %
    print(f"  Ngôn ngữ phát hiện: {info.language} ({info.language_probability:.0%})")
    print(f"  Tổng thời lượng   : {total_duration:.1f}s")
    print(f"  {'─'*60}")

    try:
        with open(srt_output_path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments, 1):
                text = segment.text.strip()
                start_fmt = format_time_srt(segment.start)
                end_fmt = format_time_srt(segment.end)

                # Tính % dựa trên thời gian kết thúc của segment
                pct = min(int(segment.end / total_duration * 100), 99) if total_duration > 0 else 0

                f.write(f"{i}\n{start_fmt} --> {end_fmt}\n{text}\n\n")
                print(f"  [{pct:3d}%] [{start_fmt} → {end_fmt}]  {text}")

        print(f"  {'─'*60}")
        print(f"  [100%] Hoàn tất transcribe → {srt_output_path}")
        return srt_output_path

    except Exception as e:
        print(f"\n❌ Lỗi trong quá trình giải mã: {e}")
        raise
