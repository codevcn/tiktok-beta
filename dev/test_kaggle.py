"""
Test script for converting a video to 9:16 with FFmpeg on Kaggle only.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent


def _escape_drawtext_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace(",", "\\,")
    )


def _resolve_existing_input(input_file: str) -> str:
    input_path = Path(input_file)
    candidates = [input_path]

    if not input_path.is_absolute():
        candidates.extend(
            [
                Path.cwd() / input_path,
                SCRIPT_DIR / input_path,
                PROJECT_ROOT / input_path,
                PROJECT_ROOT / "dev" / input_path,
            ]
        )

    seen: set[Path] = set()
    tried: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        tried.append(resolved)
        if resolved.exists():
            return str(resolved)

    tried_text = "\n".join(f"  - {path}" for path in tried)
    raise FileNotFoundError(
        f"Input video not found: {input_file}\nTried:\n{tried_text}\n"
        "When running from Kaggle with `!python dev/test_windows.py`, "
        "put the test video at `dev/input.mp4` or pass an existing path."
    )


def _resolve_output_path(output_file: str) -> str:
    output_path = Path(output_file)
    if output_path.is_absolute():
        return str(output_path)
    return str((SCRIPT_DIR / output_path).resolve())


def _detect_platform(platform: str) -> str:
    if platform != "auto":
        return platform
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def _first_existing_font(paths: list[str]) -> str | None:
    for path in paths:
        if os.path.exists(path):
            return path
    return None


def _platform_settings(platform: str) -> tuple[str | None, list[tuple[str, list[str]]]]:
    detected = _detect_platform(platform)

    if detected == "windows":
        font_path = "C\\:/Windows/Fonts/arial.ttf"
        encoders = [
            (
                "h264_amf",
                [
                    "-c:v",
                    "h264_amf",
                    "-rc",
                    "cqp",
                    "-qp_i",
                    "19",
                    "-qp_p",
                    "19",
                    "-quality",
                    "quality",
                ],
            ),
            ("libx264", ["-c:v", "libx264", "-preset", "fast", "-crf", "23"]),
        ]
        return font_path, encoders

    if detected == "macos":
        font_path = _first_existing_font(
            [
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            ]
        )
        encoders = [
            ("h264_videotoolbox", ["-c:v", "h264_videotoolbox", "-b:v", "8M"]),
            ("libx264", ["-c:v", "libx264", "-preset", "fast", "-crf", "23"]),
        ]
        return font_path, encoders

    font_path = _first_existing_font(
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    )
    encoders = [
        ("h264_nvenc", ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "23"]),
        ("libx264", ["-c:v", "libx264", "-preset", "fast", "-crf", "23"]),
    ]
    return font_path, encoders


def read_stderr(process: subprocess.Popen, total_duration: float, error_log: list[str]):
    time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})")

    if process.stderr is None:
        return

    for line in process.stderr:
        error_log.append(line)
        match = time_pattern.search(line)
        if match:
            cur_sec = sum(
                x * f for x, f in zip(map(float, match.groups()), [3600, 60, 1])
            )
            progress = min((cur_sec / total_duration) * 100, 99.9)
            sys.stdout.write(
                f"\rProgress: {progress:>5.1f}% | {cur_sec:.2f}s / {total_duration:.2f}s"
            )
            sys.stdout.flush()


def _get_duration(input_file: str) -> float:
    probe_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        input_file,
    ]
    try:
        return float(
            subprocess.check_output(probe_cmd, stderr=subprocess.STDOUT).strip()
        )
    except FileNotFoundError as e:
        raise RuntimeError("ffprobe not found. Please install FFmpeg first.") from e
    except subprocess.CalledProcessError as e:
        output = e.output.decode("utf-8", errors="replace") if e.output else ""
        raise RuntimeError(f"ffprobe failed for {input_file}:\n{output}") from e


def _build_filter(
    top_text: str,
    bottom_text: str,
    font_path: str | None,
    target_w: int,
    target_h: int,
    video_h: int,
) -> str:
    pad_h = (target_h - video_h) // 2
    font_arg = f":fontfile='{font_path}'" if font_path else ""
    escaped_top_text = _escape_drawtext_text(top_text)
    escaped_bottom_text = _escape_drawtext_text(bottom_text)

    return (
        f"[0:v]split=2[main][temp];"
        f"[temp]trim=start_frame=0:end_frame=1,"
        f"loop=loop=9999:size=1,setpts=PTS-STARTPTS,"
        f"boxblur=25:1,"
        f"split=2[blurred1][blurred2];"
        f"[blurred1]scale={target_w}:{pad_h}:force_original_aspect_ratio=increase,"
        f"crop={target_w}:{pad_h}[tp];"
        f"[blurred2]scale={target_w}:{pad_h}:force_original_aspect_ratio=increase,"
        f"crop={target_w}:{pad_h}[bp];"
        f"[main]scale={target_w}:{video_h}[mid];"
        f"[tp][mid][bp]vstack=inputs=3[combined];"
        f"[combined]"
        f"drawtext=text='{escaped_top_text}':fontcolor=white:fontsize=70"
        f":x=(w-text_w)/2:y=({pad_h}-text_h)/2{font_arg},"
        f"drawtext=text='{escaped_bottom_text}':fontcolor=white:fontsize=60"
        f":x=(w-text_w)/2:y=h-({pad_h}+text_h)/2{font_arg}[v]"
    )


def _run_ffmpeg(cmd: list[str], total_duration: float, encoder_name: str) -> bool:
    start_time = time.time()
    error_log: list[str] = []

    print(f"Using encoder: {encoder_name}")
    try:
        process = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as e:
        raise RuntimeError("ffmpeg not found. Please install FFmpeg first.") from e

    stderr_thread = threading.Thread(
        target=read_stderr,
        args=(process, total_duration, error_log),
        daemon=True,
    )
    stderr_thread.start()

    dynamic_timeout = total_duration * 3 + 120
    try:
        process.wait(timeout=dynamic_timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        print(f"\nEncoder timeout after {dynamic_timeout:.0f}s: {encoder_name}")
        return False

    stderr_thread.join(timeout=5)

    elapsed = time.time() - start_time
    if process.returncode == 0:
        print(f"\nDone. Elapsed: {elapsed:.2f}s")
        return True

    print(
        f"\nFFmpeg failed with encoder {encoder_name}. Return code: {process.returncode}"
    )
    print("--- FFmpeg tail ---")
    for line in error_log[-20:]:
        print(line, end="")
    return False


def convert_916(
    input_file: str,
    output_file: str,
    top_text: str,
    bottom_text: str,
    platform: str = "auto",
) -> str:
    input_file = _resolve_existing_input(input_file)
    output_file = _resolve_output_path(output_file)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    total_duration = _get_duration(input_file)
    print(f"Input: {input_file}")
    print(f"Output: {output_file}")
    print(f"Duration: {total_duration:.2f}s")

    font_path, encoder_candidates = _platform_settings(platform)
    if font_path:
        print(f"Font: {font_path}")
    else:
        print("Font: FFmpeg/fontconfig default")

    target_w, target_h = 1080, 1920
    video_h = 608
    filter_complex = _build_filter(
        top_text,
        bottom_text,
        font_path,
        target_w,
        target_h,
        video_h,
    )

    for encoder_name, encoder_opts in encoder_candidates:
        cmd = [
            "ffmpeg",
            "-i",
            input_file,
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "0:a?",
            *encoder_opts,
            "-c:a",
            "copy",
            "-shortest",
            "-movflags",
            "+faststart",
            output_file,
            "-y",
        ]

        if _run_ffmpeg(cmd, total_duration, encoder_name):
            return output_file

        print(f"Trying next encoder after {encoder_name} failure...")

    raise RuntimeError("All encoders failed.")


if __name__ == "__main__":
    convert_916(
        input_file="input.mp4",
        output_file="output.mp4",
        top_text="Top title",
        bottom_text="Bottom title",
        platform="auto",
    )
