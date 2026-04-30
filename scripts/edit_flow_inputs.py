"""
Paste this whole file into a Kaggle code cell, edit FLOW_INPUTS, then run it.
It will overwrite data/video/input/flow-inputs.json in the current project.

Run from the project root:
  python scripts/edit_flow_inputs.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# ============================================================
# EDIT CONFIG HERE
# ============================================================

FLOW_INPUTS: dict[str, Any] = {
    "parallel_execution": False,
    "use_gpu": True,
    "links": [
        {
            "link": "https://youtu.be/3mxblcBZgqM",
            "original_lang_code": "ja",
            "target_lang_code": "ja",
            "subtitle_configs": {
                "fontname": "Arial",
                "fontsize": 18,
                "primarycolor": "255,255,0",
                "outlinecolor": "0,0,0",
                "backcolor": "0,0,0,128",
                "outline": 2.0,
                "shadow": 1.0,
                "bold": True,
                "alignment": "BOTTOM_CENTER",
                "marginv": 10,
                "marginl": 0,
                "marginr": 0,
            },
            # Delete this "watermark" block if you do not need watermark removal.
            # "watermark": {
            #     "x1": 1111,
            #     "y1": 3,
            #     "x2": 1273,
            #     "y2": 164,
            # },
            "flows": [
                # Use this flow to translate subtitle before burning it.
                # {"name": "burn_sub_to_video_with_translate"},
                # Use this flow to burn the fixed original subtitle directly.
                {"name": "burn_sub_to_video_no_translate"},
            ],
        },
        # Add more link entries here if needed:
        # {
        #     "link": "https://youtu.be/ANOTHER_VIDEO_ID",
        #     "original_lang_code": "en",
        #     "target_lang_code": "vi",
        #     "subtitle_configs": {
        #         "fontname": "Arial",
        #         "fontsize": 18,
        #         "primarycolor": "255,255,0",
        #         "outlinecolor": "0,0,0",
        #         "backcolor": "0,0,0,128",
        #         "outline": 2.0,
        #         "shadow": 1.0,
        #         "bold": True,
        #         "alignment": "BOTTOM_CENTER",
        #         "marginv": 10,
        #         "marginl": 0,
        #         "marginr": 0,
        #     },
        #     "flows": [
        #         {"name": "burn_sub_to_video_with_translate"},
        #     ],
        # },
    ],
}


# ============================================================
# WRITE CONFIG FILE
# ============================================================

CONFIG_PATH = Path("data/video/input/flow-inputs.json")
VALID_FLOW_NAMES = {
    "burn_sub_to_video_with_translate",
    "burn_sub_to_video_no_translate",
}


def validate_config(config: dict[str, Any]) -> None:
    links = config.get("links")
    if not isinstance(links, list) or not links:
        raise ValueError("FLOW_INPUTS['links'] must be a non-empty list.")

    for idx, entry in enumerate(links):
        if not isinstance(entry, dict):
            raise ValueError(f"links[{idx}] must be an object.")
        if not entry.get("link"):
            raise ValueError(f"links[{idx}]['link'] is required.")

        flows = entry.get("flows")
        if not isinstance(flows, list) or not flows:
            raise ValueError(f"links[{idx}]['flows'] must be a non-empty list.")

        for flow in flows:
            name = flow.get("name") if isinstance(flow, dict) else None
            if name not in VALID_FLOW_NAMES:
                raise ValueError(
                    f"Invalid flow name in links[{idx}]: {name!r}. "
                    f"Valid names: {sorted(VALID_FLOW_NAMES)}"
                )


def save_config(config: dict[str, Any], path: Path = CONFIG_PATH) -> None:
    validate_config(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
        f.write("\n")


save_config(FLOW_INPUTS)

print(f"Updated: {CONFIG_PATH}")
print(json.dumps(FLOW_INPUTS, ensure_ascii=False, indent=2))
