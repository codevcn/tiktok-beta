"""
Entry point - Hiển thị menu chọn quy trình xử lý video.
"""

import sys

from auto_burn_sub_to_video import main as run_pipeline


FLOWS: dict[int, dict] = {
    1: {
        "name": "Tự động gắn sub CÓ dịch thuật",
        "description": "Download → Xóa watermark → Transcribe → Sửa typo → Dịch → Burn sub",
        "options": {"translate": True},
    },
    2: {
        "name": "Tự động gắn sub KHÔNG dịch thuật",
        "description": "Download → Xóa watermark → Transcribe → Sửa typo → Burn sub",
        "options": {"translate": False},
    },
}


def print_menu() -> None:
    print("\n" + "=" * 55)
    print("  🎬  QUIIN VIDEO PROCESSOR  —  Chọn quy trình")
    print("=" * 55)
    for num, flow in FLOWS.items():
        print(f"\n  [{num}] {flow['name']}")
        print(f"       {flow['description']}")
    print("\n" + "-" * 55)



def get_user_choice() -> int:
    while True:
        try:
            raw = input("  Nhập số thứ tự quy trình và nhấn Enter: ").strip()
            choice = int(raw)
            if choice in FLOWS:
                return choice
            else:
                print(
                    f"  ❌ Không có quy trình số {choice}. Vui lòng chọn từ {list(FLOWS.keys())}."
                )
        except ValueError:
            print("  ❌ Vui lòng nhập một số nguyên hợp lệ.")
        except (KeyboardInterrupt, EOFError):
            print("\n\n  👋 Đã hủy. Tạm biệt!")
            sys.exit(0)


def main() -> None:
    print_menu()
    choice = get_user_choice()

    flow = FLOWS[choice]
    options: dict = dict(flow["options"])  # copy để không ảnh hưởng FLOWS gốc

    print(f"\n  ✅ Bắt đầu quy trình: [{choice}] {flow['name']}\n")

    run_pipeline(options)


if __name__ == "__main__":
    main()
