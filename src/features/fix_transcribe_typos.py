"""
Sửa lỗi typo trong 1 file srt.
"""

import os
from core.ai_client import generate_with_failover, clean_markdown_response


def get_prompt(srt_text: str) -> str:
    return f"""
You are a subtitle correction engine.

Your task is to correct wrongly transcribed words in an SRT subtitle text and return the corrected result as a valid SRT file.

Input:
- The input is a full SRT subtitle text.
- Each subtitle block contains:
  1. numeric index
  2. timestamp line
  3. one or more text lines

Your goals:
1. Fix speech-to-text transcription mistakes, including:
   - misrecognized words
   - wrong homophones
   - broken names or terms
   - missing or incorrect diacritics if the language requires them
   - obvious punctuation and spacing mistakes only when they improve readability
2. Replace wrongly transcribed words with words that best match the intended meaning from context.
3. Preserve the original meaning as much as possible.
4. Do NOT translate.
5. Do NOT rewrite stylistically unless necessary to fix an obvious transcription error.
6. Do NOT merge or split subtitle blocks.
7. Do NOT change subtitle indices.
8. Do NOT change timestamps.
9. Preserve line breaks inside each subtitle block whenever possible.
10. If a segment is unclear, keep the original text rather than inventing content.

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

    with open(output_srt_path, "w", encoding="utf-8") as f:
        f.write(result_text)

    print(f"  ✅ Sửa lỗi hoàn tất → {output_srt_path}")
    return output_srt_path
