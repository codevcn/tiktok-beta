"""
Sửa lỗi typo trong 1 file srt.
"""

import os
from core.ai_client import generate_with_failover, clean_markdown_response
from utils.srt_validation import SrtValidationError, coerce_validated_srt


def get_prompt(srt_text: str) -> str:
    return f"""You are a subtitle correction and punctuation restoration engine.

Your task is to correct wrongly transcribed words and restore natural punctuation in an SRT subtitle text, then return the corrected result as a valid SRT file.

Input:
- The input is a full SRT subtitle text.
- Each subtitle block contains:
  1. numeric index
  2. timestamp line
  3. one or more subtitle text lines

What you may change:
1. Fix speech-to-text transcription mistakes, including:
   - misrecognized words
   - wrong homophones
   - broken names or terms
   - missing or incorrect diacritics if the language requires them
2. Restore natural punctuation inside subtitle text when it improves readability:
   - add periods, commas, question marks, exclamation marks, colons, semicolons, quotation marks, or language-appropriate equivalents
   - fix spacing around punctuation
   - keep punctuation natural for the detected/source language
3. Replace wrongly transcribed words with words that best match the intended meaning from context.

Strict structural rules:
1. Do NOT translate.
2. Do NOT rewrite stylistically unless necessary to fix an obvious transcription error.
3. Do NOT merge, split, remove, or add subtitle blocks.
4. Do NOT change subtitle indices.
5. Do NOT change timestamps.
6. Preserve the original order of all subtitle blocks.
7. Preserve line breaks inside each subtitle block whenever possible.
8. If a segment is unclear, keep the original text rather than inventing content.
9. The output will be rejected if the number of blocks, any index, or any timestamp differs from the input.

Output requirements:
- Return the full corrected subtitle content in valid SRT format.
- Output only the corrected SRT text.
- Do not return JSON.
- Do not use markdown.
- Do not add explanations, notes, or comments.
- Do not wrap the output in code fences.

Now process this SRT content:

{srt_text}
"""


def fix_typos_in_srt(input_srt_path: str, output_srt_path: str) -> str:
    if not os.path.exists(input_srt_path):
        raise FileNotFoundError(f"Không tìm thấy file: {input_srt_path}")

    with open(input_srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()

    print("🤖 Đang gửi phụ đề để sửa lỗi chính tả...")

    result_text = generate_with_failover(
        prompt=get_prompt(srt_content),
        task_label="Sửa lỗi chính tả",
    )
    result_text = clean_markdown_response(result_text)
    try:
        result_text = coerce_validated_srt(
            srt_content,
            result_text,
            "typo and punctuation correction output",
        )
        print("  -> SRT validation passed: block count, indices, and timestamps unchanged.")
    except SrtValidationError as e:
        print(f"  [SRT validation failed] {e}")
        raise

    with open(output_srt_path, "w", encoding="utf-8") as f:
        f.write(result_text)

    print(f"  ✅ Sửa lỗi hoàn tất → {output_srt_path}")
    return output_srt_path
