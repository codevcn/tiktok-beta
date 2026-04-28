- Dùng prompt sau để gửi đến gemini yêu cầu dịch bản SRT đã transcribe:

```
You are a professional subtitle translator with strong expertise in the SRT subtitle format.

Your task is to translate the SRT subtitle content below into the target language: [TARGET_LANGUAGE].

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

[SOURCE_SRT]

```
