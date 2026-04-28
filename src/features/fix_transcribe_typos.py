"""
Sửa lỗi typo trong 1 file srt.
"""

import os
from google import genai


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
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "Lỗi: Không tìm thấy biến môi trường GOOGLE_API_KEY. Vui lòng cấu hình ở file .env"
        )

    client = genai.Client(api_key=api_key)

    if not os.path.exists(input_srt_path):
        raise FileNotFoundError(f"Không tìm thấy file: {input_srt_path}")

    with open(input_srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()

    print("🤖 [HTTP → Gemini] Đang gửi phụ đề để sửa lỗi chính tả... (vui lòng đợi)")
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=get_prompt(srt_content),
        )

        result_text = (response.text or "").strip()
        # Loại bỏ markdown nếu AI lỡ sinh ra
        if result_text.startswith("```"):
            lines = result_text.splitlines()
            if lines:
                lines = lines[1:]  # Bỏ dòng đầu chứa ```
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]  # Bỏ dòng cuối
            result_text = "\n".join(lines).strip()

        with open(output_srt_path, "w", encoding="utf-8") as f:
            f.write(result_text)

        print(f"  ✅ [HTTP ← Gemini] Sửa lỗi hoàn tất → {output_srt_path}")
        return output_srt_path
    except Exception as e:
        print(f"❌ Có lỗi trong quá trình sử dụng API: {e}")
        raise
