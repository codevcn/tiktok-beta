- Description:

This file contains the configuration for the video processing tool. It specifies the parallel execution mode, the list of video links to process, the target language code for the translated subtitle, and the subtitle configuration. The code must use this file as input for program instead of loading video from "input" folder.

- Example:

```json
{
  "parallel-execution": false,
  "links": [
    {
      "link": "https://www.youtube.com/watch?v=420r7H7K0Qc",
      "target-lang-code": "vi",
      "subtitle-configs": {
        "fontname": "Arial",
        "fontsize": 24,
        "primarycolor": "255,255,0",
        "outlinecolor": "0,0,0",
        "backcolor": "0,0,0,128",
        "outline": 2.0,
        "shadow": 1.0,
        "bold": true,
        "alignment": "BOTTOM_CENTER",
        "marginv": 30,
        "marginl": 0,
        "marginr": 0
      }
    }
  ]
}
```

- Explanation:
  - "parallel-execution": If true, the tool will process all links in the "links" array in parallel. If false, it will process them sequentially.
  - "links": An array of video links to process.
  - "original-lang-code": The original language code of the video in standard ISO 639-1. If not provided, the tool will try to detect it automatically.
  - "target-lang-code": The target language code for the translated subtitle in standard ISO 639-1.
  - "subtitle-configs": An object containing the subtitle configuration.
    - "fontname": The font name for the subtitle.
    - "fontsize": The font size for the subtitle.
    - "primarycolor": The primary color of the subtitle in RGB format (e.g., "255,255,0" for yellow).
    - "outlinecolor": The outline color of the subtitle in RGB format (e.g., "0,0,0" for black).
    - "backcolor": The background color of the subtitle in RGBA format (e.g., "0,0,0,128" for black with 50% transparency).
    - "outline": The outline width of the subtitle.
    - "shadow": The shadow width of the subtitle.
    - "bold": Whether the subtitle should be bold.
    - "alignment": The alignment of the subtitle.
    - "marginv": The vertical margin of the subtitle.
    - "marginl": The left margin of the subtitle.
    - "marginr": The right margin of the subtitle.
  - "watermark": An object containing the watermark configuration.
    - "x1": The x-coordinate of the top-left corner of the watermark.
    - "y1": The y-coordinate of the top-left corner of the watermark.
    - "x2": The x-coordinate of the bottom-right corner of the watermark.
    - "y2": The y-coordinate of the bottom-right corner of the watermark.
