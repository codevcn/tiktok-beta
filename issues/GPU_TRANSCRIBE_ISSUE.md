# GPU Transcribe Issue

## Summary

When `use_gpu` is enabled in `data/video/input/links.json`, the pipeline may appear to stop immediately after the transcription step finishes.

This is misleading: the Python flow itself is not intentionally stopping there. The more likely situation is that the process exits at the native runtime layer used by `faster-whisper` / `CTranslate2` / CUDA on Windows.

When the same pipeline is run with `use_gpu: false`, it completes normally:

- transcribe
- typo correction with Gemini
- subtitle burn
- final output video

## Observed Behavior

### GPU run

Observed in `runtime.log` from the GPU attempt:

- transcription finished successfully
- the process returned directly to the terminal prompt
- no `--- BƯỚC 4: SỬA LỖI CHÍNH TẢ BẰNG AI ---`
- no Python traceback
- no normal pipeline error message from `auto_burn_sub_to_video.py`

This strongly suggests a hard process exit rather than a regular Python exception.

### CPU run

Observed in the CPU run:

- `Transcribe` completed normally
- `BƯỚC 4` started and completed
- subtitle burn completed
- `output_video.mp4` was created

Files produced successfully in the CPU run:

- `raw_subtitle.srt`
- `fixed_subtitle.srt`
- `output_video.mp4`

## Why This Happens

The likely cause is not the pipeline logic itself, but the GPU backend stack used by the transcription step.

The relevant code is in `src/features/transcribe_audio_file.py`, where:

- `faster-whisper` is used
- `WhisperModel(..., device="cuda", compute_type="float16")` is selected when GPU is enabled
- NVIDIA DLL directories are manually added and preloaded on Windows before importing `faster_whisper`

This setup depends on multiple native components being compatible:

- NVIDIA driver
- CUDA runtime
- cuDNN
- cuBLAS
- `ctranslate2`
- `faster-whisper`
- Windows DLL loading behavior

If these are only partially compatible, the model may still appear to run, but the Python process can terminate unexpectedly when:

- GPU resources are released
- CUDA context is finalized
- a native library hits an unrecoverable error outside Python exception handling

That explains why:

- transcription output may still be written
- the process may die immediately after transcription
- no Python traceback is shown

## Why CPU Works

When CPU mode is used, the transcription step runs with:

- `device="cpu"`
- `compute_type="int8"`

This avoids the CUDA runtime entirely.

As a result:

- no GPU DLL dependency chain is involved
- no CUDA context is created
- no GPU-native teardown occurs after transcription
- the pipeline remains stable and continues to the next steps

In the observed CPU run, the full pipeline completed successfully end-to-end.

## CPU vs GPU Comparison

| Aspect                               | GPU mode           | CPU mode |
| ------------------------------------ | ------------------ | -------- |
| Stability in current environment     | Unstable           | Stable   |
| Transcription speed                  | Potentially faster | Slower   |
| Dependency complexity                | High               | Low      |
| Requires CUDA/cuDNN compatibility    | Yes                | No       |
| Risk of silent native crash          | Higher             | Very low |
| End-to-end pipeline success observed | No                 | Yes      |

## What We Know From Current Evidence

1. The flow logic in `src/auto_burn_sub_to_video.py` is correct.
2. The pipeline does not intentionally stop after transcription.
3. The problem does not appear when CPU mode is used.
4. The issue is most likely in the GPU transcription backend, not in:
   - Gemini typo correction
   - subtitle burning
   - video download
   - menu flow logic

## Recommended Fixes

### Safe short-term fix

Use CPU mode by default:

```json
{
  "use_gpu": false
}
```

This is the most reliable option in the current environment.

### Better medium-term fix

Add a controlled GPU fallback strategy for transcription:

1. Try transcription with GPU.
2. If GPU initialization or execution fails, retry automatically on CPU.
3. Continue the rest of the pipeline on CPU-transcribed output.

Note: this only helps if the GPU failure raises a normal exception. If the process exits hard at native level, fallback inside the same process may not be enough.

### More robust engineering fix

Move GPU transcription into a separate subprocess:

1. Spawn a child process dedicated to GPU transcription.
2. If the child exits abnormally, detect it from the parent process.
3. Retry transcription on CPU from the parent process.
4. Continue the pipeline safely.

This is the most reliable way to recover from silent native crashes.

### Environment-level fixes to investigate

Check compatibility between:

- installed NVIDIA driver
- CUDA runtime version
- cuDNN DLLs in `.venv`
- `faster-whisper`
- `ctranslate2`

Also review whether manual DLL preloading in `src/features/transcribe_audio_file.py` is necessary or if it is making the Windows environment more fragile.

## Practical Recommendation

For now, use CPU mode for production runs.

If GPU support is still desired, the next implementation step should be:

1. keep CPU as the safe default
2. isolate GPU transcription into a subprocess
3. add automatic fallback to CPU when the GPU subprocess exits abnormally

## Real-World Tradeoff

In the current project state:

- GPU offers possible speed improvements mainly for transcription
- CPU offers proven end-to-end reliability

Because the full workflow matters more than only one faster step, CPU is currently the better operational choice unless the GPU runtime is stabilized first.

(Đã giải quyết)
