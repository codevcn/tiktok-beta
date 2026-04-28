"""
Worker subprocess cho GPU transcription.
File này được thiết kế để chạy như một process độc lập, cách ly CUDA runtime
khỏi pipeline chính. Nếu CUDA crash, chỉ process con chết, process cha vẫn sống.

Cách dùng:
    python _transcribe_worker.py <audio_path> <srt_output_path> <device> <compute_type> [language]

Exit code 0 = thành công, khác 0 = thất bại.
"""

import os
import sys
import glob

# --- PRELOAD NVIDIA DLLs (chỉ cần khi chạy GPU) ---
if sys.platform == "win32":
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
            os.add_dll_directory(_d)

    import ctypes
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
                pass

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from faster_whisper import WhisperModel


def format_time_srt(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def run(audio_path: str, srt_output_path: str, device: str, compute_type: str, language: str | None):
    if not os.path.exists(audio_path):
        print(f"  ❌ Không tìm thấy file: {audio_path}", flush=True)
        sys.exit(1)

    lang_label = language if language else "auto-detect"
    print(f"  → Đang tải model Whisper large-v3 ({device.upper()} / {compute_type}) | ngôn ngữ: {lang_label}...", flush=True)
    model = WhisperModel("large-v3", device=device, compute_type=compute_type)

    print("  → Đang phân tích âm thanh...\n", flush=True)
    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        language=language,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    total_duration = info.duration
    print(f"  Ngôn ngữ phát hiện: {info.language} ({info.language_probability:.0%})", flush=True)
    print(f"  Tổng thời lượng   : {total_duration:.1f}s", flush=True)
    print(f"  {'─'*60}", flush=True)

    with open(srt_output_path, "w", encoding="utf-8") as f:
        for i, segment in enumerate(segments, 1):
            text = segment.text.strip()
            start_fmt = format_time_srt(segment.start)
            end_fmt = format_time_srt(segment.end)
            pct = min(int(segment.end / total_duration * 100), 99) if total_duration > 0 else 0
            f.write(f"{i}\n{start_fmt} --> {end_fmt}\n{text}\n\n")
            print(f"  [{pct:3d}%] [{start_fmt} → {end_fmt}]  {text}", flush=True)

    print(f"  {'─'*60}", flush=True)
    print(f"  [100%] Hoàn tất transcribe → {srt_output_path}", flush=True)

    # Giải phóng model và CUDA context trước khi exit
    del model


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python _transcribe_worker.py <audio_path> <srt_output_path> <device> <compute_type> [language]")
        sys.exit(2)

    audio_path = sys.argv[1]
    srt_output_path = sys.argv[2]
    device = sys.argv[3]
    compute_type = sys.argv[4]
    language = sys.argv[5] if len(sys.argv) > 5 else None

    try:
        run(audio_path, srt_output_path, device, compute_type, language)
    except Exception as e:
        print(f"\n❌ Lỗi trong quá trình giải mã: {e}", flush=True)
        sys.exit(1)
