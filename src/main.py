"""
Entry point - Tự động chạy quy trình dựa trên cấu hình trong flow-inputs.json.
"""

import os
import sys
import json

from auto_burn_sub_to_video import main as run_pipeline


def main() -> None:
    config_path = os.path.join("data", "video", "input", "flow-inputs.json")
    if not os.path.exists(config_path):
        print(f"❌ Không tìm thấy file cấu hình: {config_path}")
        sys.exit(1)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Lỗi khi đọc file cấu hình {config_path}: {e}")
        sys.exit(1)

    flows = config.get("flows", {})
    
    if flows.get("auto_burn_sub_to_video_with_translate"):
        print("\n  ✅ Bắt đầu quy trình: Tự động gắn sub CÓ dịch thuật\n")
        run_pipeline({"translate": True})
    elif flows.get("auto_burn_sub_to_video_no_translate"):
        print("\n  ✅ Bắt đầu quy trình: Tự động gắn sub KHÔNG dịch thuật\n")
        run_pipeline({"translate": False})
    else:
        print("❌ Không có quy trình nào được bật (true) trong 'flows' của flow-inputs.json.")
        sys.exit(1)


if __name__ == "__main__":
    main()
