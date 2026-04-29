"""
Entry point - Tự động chạy quy trình dựa trên cấu hình trong flow-inputs.json.
Flows được cấu hình per-link, không cần chọn flow ở cấp top-level.
"""

from auto_burn_sub_to_video import main as run_pipeline


def main() -> None:
    run_pipeline()


if __name__ == "__main__":
    main()
