"""
Transcribe audio thành SRT.

Khi use_gpu=True:
  → Chạy trong subprocess riêng để cách ly CUDA runtime.
  → Nếu subprocess crash (do CUDA teardown), tự động fallback sang CPU.

Khi use_gpu=False:
  → Chạy trực tiếp trong process hiện tại (an toàn, không cần CUDA).
"""

import os
import sys
import subprocess


def _run_in_subprocess(
    audio_path: str,
    srt_output_path: str,
    device: str,
    compute_type: str,
    language: str | None,
) -> int:
    """Spawn worker subprocess và stream output realtime. Trả về exit code."""
    worker_script = os.path.join(os.path.dirname(__file__), "_transcribe_worker.py")
    cmd = [
        sys.executable,
        worker_script,
        audio_path,
        srt_output_path,
        device,
        compute_type,
    ]
    if language:
        cmd.append(language)

    proc = subprocess.Popen(
        cmd,
        stdout=sys.stdout,
        stderr=sys.stderr,
        cwd=os.getcwd(),
    )
    proc.wait()
    return proc.returncode


def _run_cpu_inline(
    audio_path: str,
    srt_output_path: str,
    language: str | None,
) -> str:
    """Chạy transcribe CPU trực tiếp trong process hiện tại (không cần CUDA)."""
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    from faster_whisper import WhisperModel

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Không tìm thấy file: {audio_path}")

    lang_label = language if language else "auto-detect"
    print(f"  → Đang tải model Whisper large-v3 (CPU / int8) | ngôn ngữ: {lang_label}...")
    model = WhisperModel("large-v3", device="cpu", compute_type="int8")

    print("  → Đang phân tích âm thanh...\n")
    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        language=language,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    total_duration = info.duration
    print(f"  Ngôn ngữ phát hiện: {info.language} ({info.language_probability:.0%})")
    print(f"  Tổng thời lượng   : {total_duration:.1f}s")
    print(f"  {'─'*60}")

    try:
        with open(srt_output_path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments, 1):
                text = segment.text.strip()
                start_fmt = _format_time_srt(segment.start)
                end_fmt = _format_time_srt(segment.end)
                pct = min(int(segment.end / total_duration * 100), 99) if total_duration > 0 else 0
                f.write(f"{i}\n{start_fmt} --> {end_fmt}\n{text}\n\n")
                print(f"  [{pct:3d}%] [{start_fmt} → {end_fmt}]  {text}")

        print(f"  {'─'*60}")
        print(f"  [100%] Hoàn tất transcribe → {srt_output_path}")
        return srt_output_path

    except Exception as e:
        print(f"\n❌ Lỗi trong quá trình giải mã: {e}")
        raise


def _format_time_srt(seconds: float) -> str:
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
        use_gpu: True → chạy trong subprocess với CUDA (float16), auto-fallback CPU nếu crash;
                 False → chạy trực tiếp với CPU (int8).
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Không tìm thấy file: {audio_path}")

    if use_gpu:
        # ── GPU: chạy trong subprocess để cách ly CUDA runtime ──
        print("  ℹ️  GPU mode → chạy transcribe trong subprocess riêng (cách ly CUDA)")
        exit_code = _run_in_subprocess(audio_path, srt_output_path, "cuda", "float16", language)

        if exit_code == 0 and os.path.exists(srt_output_path):
            return srt_output_path

        # Subprocess crash (CUDA teardown) hoặc lỗi → fallback CPU
        print(f"\n  ⚠️  GPU subprocess kết thúc bất thường (exit code: {exit_code})")
        print("  ⚠️  Tự động chuyển sang CPU để thử lại...\n")
        return _run_cpu_inline(audio_path, srt_output_path, language)

    else:
        # ── CPU: chạy trực tiếp, an toàn ──
        return _run_cpu_inline(audio_path, srt_output_path, language)
