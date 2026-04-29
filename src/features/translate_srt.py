"""
Dịch nội dung SRT sang ngôn ngữ đích bằng AI.
"""

import os
from core.ai_client import generate_with_failover, clean_markdown_response


def get_translate_prompt(srt_text: str, target_lang_code: str) -> str:
    return f"""You are a professional subtitle translator with strong expertise in the SRT subtitle format.

Your task is to translate the SRT subtitle content below into the target language: {target_lang_code}.

Mandatory requirements:

1. Preserve the original SRT format exactly:
   - Keep all subtitle index numbers unchanged.
   - Keep all timestamps unchanged.
   - Keep the original order of all subtitle blocks.
   - Keep the blank line between subtitle blocks.
   - Do not add any introduction, explanation, notes, markdown, or any content outside the translated SRT.

2. Translate only the subtitle text:
   - Do not translate subtitle index numbers.
   - Do not translate timestamps.
   - Do not change the file structure.
   - Do not merge, split, remove, or add subtitle blocks.

3. The translation must sound natural to native speakers of the target language:
   - Use fluent, idiomatic, context-appropriate wording.
   - Avoid literal or word-for-word translation.
   - Prioritize expressions that native speakers would actually use.
   - Preserve the tone, emotion, register, and level of formality/informality of the original text.

4. Do not alter the core meaning:
   - Preserve the meaning, information, intent, tone, and flow of the original subtitles.
   - Do not add interpretation or extra details.
   - Do not omit important information.
   - Do not censor, soften, rewrite, or embellish the original content.

5. Proper nouns, terminology, brands, and place names:
   - Keep them unchanged unless there is a widely accepted translation in the target language.
   - Translate technical or domain-specific terms accurately and naturally according to context.

6. Output requirements:
   - Return only the translated SRT content.
   - Do not wrap the output in a code block.
   - Do not add a title.
   - Do not add explanations or comments.

Here is the SRT content to translate:

{srt_text}
"""


def translate_srt(
    input_srt_path: str, output_srt_path: str, target_lang_code: str
) -> str:
    """
    Dịch nội dung file SRT sang ngôn ngữ đích bằng AI.

    Args:
        input_srt_path: Đường dẫn file SRT đầu vào (đã sửa typo).
        output_srt_path: Đường dẫn file SRT đầu ra sau khi dịch.
        target_lang_code: Mã ngôn ngữ đích theo chuẩn ISO 639-1 (ví dụ: "vi", "en", "ja").

    Returns:
        Đường dẫn file SRT đã dịch.
    """
    if not os.path.exists(input_srt_path):
        raise FileNotFoundError(f"Không tìm thấy file: {input_srt_path}")

    with open(input_srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()

    print(f"🌐 Đang dịch phụ đề sang [{target_lang_code}]...")

    result_text = generate_with_failover(
        prompt=get_translate_prompt(srt_content, target_lang_code),
        task_label=f"Dịch thuật → {target_lang_code}",
    )
    result_text = clean_markdown_response(result_text)

    with open(output_srt_path, "w", encoding="utf-8") as f:
        f.write(result_text)

    print(f"  ✅ Dịch thuật hoàn tất → {output_srt_path}")
    return output_srt_path
