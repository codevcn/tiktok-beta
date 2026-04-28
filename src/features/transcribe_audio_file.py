import os
import sys
import glob

# --- ĐẢM BẢO WINDOWS TÌM THẤY NVIDIA DLL KHI DÙNG GPU ---
# CTranslate2 (backend faster_whisper) load DLL bằng cơ chế riêng,
# không qua PATH hay add_dll_directory. Cách duy nhất đáng tin cậy:
# ép load (preload) DLL trực tiếp vào process bằng ctypes.WinDLL
# TRƯỚC khi import faster_whisper.
_venv_site = os.path.join(os.getcwd(), ".venv", "Lib", "site-packages")
_nvidia_dll_dirs = [
    os.path.join(_venv_site, "nvidia", "cublas",       "bin"),
    os.path.join(_venv_site, "nvidia", "cuda_runtime", "bin"),
    os.path.join(_venv_site, "nvidia", "cudnn",        "bin"),
    os.path.join(_venv_site, "nvidia", "cufft",        "bin"),
]

for _d in _nvidia_dll_dirs:
    if os.path.isdir(_d):
        os.environ["PATH"] = _d + ";" + os.environ.get("PATH", "")
        if sys.platform == "win32":
            os.add_dll_directory(_d)

# Preload các DLL quan trọng trước khi import faster_whisper
if sys.platform == "win32":
    import ctypes
    # Thứ tự load quan trọng: cuda_runtime → cublas → cudnn
    _dll_patterns = [
        os.path.join(_venv_site, "nvidia", "cuda_runtime", "bin", "cudart64_*.dll"),
        os.path.join(_venv_site, "nvidia", "cublas",       "bin", "cublas64_*.dll"),
        os.path.join(_venv_site, "nvidia", "cublas",       "bin", "cublasLt64_*.dll"),
        os.path.join(_venv_site, "nvidia", "cudnn",        "bin", "cudnn*.dll"),
        os.path.join(_venv_site, "nvidia", "cufft",        "bin", "cufft64_*.dll"),
    ]
    for _pattern in _dll_patterns:
        for _dll_path in sorted(glob.glob(_pattern)):
            try:
                ctypes.WinDLL(_dll_path)
            except OSError:
                pass  # DLL không load được → bỏ qua, sẽ fallback lúc runtime
# ---------------------------------------------------------

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from faster_whisper import WhisperModel



def format_time_srt(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def transcribe_audio(
    audio_path: str,
    srt_output_path: str,
    language: str | None = None,
    use_gpu: bool = False,
) -> str:
    """
    Transcribe file audio thành SRT.

    Args:
        audio_path: Đường dẫn file audio đầu vào.
        srt_output_path: Đường dẫn file SRT đầu ra.
        language: Mã ngôn ngữ ISO 639-1 (ví dụ "vi", "ja", "en").
                  None → Whisper tự động phát hiện ngôn ngữ.
        use_gpu: True → dùng CUDA (float16); False → dùng CPU (int8).
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Không tìm thấy file: {audio_path}")

    if use_gpu:
        device, compute_type = "cuda", "float16"
    else:
        device, compute_type = "cpu", "int8"

    lang_label = language if language else "auto-detect"
    print(f"  → Đang tải model Whisper large-v3 ({device.upper()} / {compute_type}) | ngôn ngữ: {lang_label}...")
    model = WhisperModel("large-v3", device=device, compute_type=compute_type)

    print("  → Đang phân tích âm thanh...\n")
    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        language=language,  # None = tự detect
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

