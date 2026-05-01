"""
ai_client.py — Multi-Tier Failover AI Client
=============================================
Hệ thống gọi AI với retry + tự động chuyển đổi mô hình theo tầng:

  Tier 1: Gemini 2.5 Flash  (chính, retry 4 lần, exponential backoff)
  Tier 2: Gemini 2.0 Flash  (dự phòng nội bộ, retry 3 lần)
  Tier 3: OpenAI GPT-4o-mini (dự phòng ngoài, retry 2 lần)

Chỉ retry khi gặp lỗi tạm thời (503, 429). Dừng ngay nếu lỗi 400/401.
"""

import os
import time
from dataclasses import dataclass

# ============================================================
# CẤU HÌNH CÁC TIER
# ============================================================


@dataclass
class TierConfig:
    """Cấu hình một tier trong hệ thống failover."""

    name: str  # Tên hiển thị (vd: "Gemini 2.5 Flash")
    provider: str  # "gemini" hoặc "openai"
    model: str  # Tên model API
    max_retries: int  # Số lần retry tối đa
    backoff_base: float  # Base time cho exponential backoff (giây)
    backoff_max: float  # Thời gian chờ tối đa (giây)
    env_key: str  # Tên biến môi trường chứa API key


# Danh sách tier theo thứ tự ưu tiên (sắp xếp từ model tốt nhất đến ít tốt hơn theo nhu cầu của project)
TIERS = [
    TierConfig(
        name="Gemini 2.5 Flash",
        provider="gemini",
        model="gemini-2.5-flash",
        max_retries=3,
        backoff_base=3.0,
        backoff_max=30.0,
        env_key="GOOGLE_API_KEY",
    ),
    TierConfig(
        name="OpenAI GPT-5.4-mini",
        provider="openai",
        model="gpt-5.4-mini",
        max_retries=2,
        backoff_base=2.0,
        backoff_max=30.0,
        env_key="OPENAI_API_KEY",
    ),
    TierConfig(
        name="Gemini 3 Flash Preview",
        provider="gemini",
        model="gemini-3-flash-preview",
        max_retries=3,
        backoff_base=2.0,
        backoff_max=60.0,
        env_key="GOOGLE_API_KEY",
    ),
    TierConfig(
        name="OpenAI GPT-5-mini",
        provider="openai",
        model="gpt-5-mini",
        max_retries=2,
        backoff_base=2.0,
        backoff_max=30.0,
        env_key="OPENAI_API_KEY",
    ),
    TierConfig(
        name="Gemini 2.5 Flash Lite",
        provider="gemini",
        model="gemini-2.5-flash-lite",
        max_retries=3,
        backoff_base=3.0,
        backoff_max=30.0,
        env_key="GOOGLE_API_KEY",
    ),
    TierConfig(
        name="OpenAI GPT-4.1-mini",
        provider="openai",
        model="gpt-4.1-mini",
        max_retries=2,
        backoff_base=2.0,
        backoff_max=30.0,
        env_key="OPENAI_API_KEY",
    ),
]


# ============================================================
# PHÂN LOẠI LỖI
# ============================================================


def _is_retryable_error(error: Exception) -> bool:
    """Kiểm tra xem lỗi có nên retry không (503, 429)."""
    error_str = str(error).lower()

    # Kiểm tra HTTP status code trong message
    retryable_codes = [
        "503",
        "429",
        "unavailable",
        "resource_exhausted",
        "rate_limit",
        "overloaded",
    ]
    return any(code in error_str for code in retryable_codes)


def _is_permanent_error(error: Exception) -> bool:
    """Kiểm tra lỗi vĩnh viễn không nên retry (400, 401, 403)."""
    error_str = str(error).lower()
    permanent_codes = [
        "400",
        "401",
        "403",
        "invalid_argument",
        "permission_denied",
        "unauthenticated",
    ]
    return any(code in error_str for code in permanent_codes)


# ============================================================
# GỌI API THEO PROVIDER
# ============================================================


def _call_gemini(model: str, api_key: str, prompt: str) -> str:
    """Gọi Gemini API và trả về text response."""
    from google import genai

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    return (response.text or "").strip()


def _call_openai(model: str, api_key: str, prompt: str) -> str:
    """Gọi OpenAI API và trả về text response."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return (response.choices[0].message.content or "").strip()


def _call_provider(tier: TierConfig, api_key: str, prompt: str) -> str:
    """Dispatch gọi API theo provider."""
    if tier.provider == "gemini":
        return _call_gemini(tier.model, api_key, prompt)
    elif tier.provider == "openai":
        return _call_openai(tier.model, api_key, prompt)
    else:
        raise ValueError(f"Provider không hỗ trợ: {tier.provider}")


# ============================================================
# LOGIC RETRY CHO MỘT TIER
# ============================================================


def _try_tier(tier: TierConfig, prompt: str) -> str | None:
    """
    Thử gọi API trên một tier với exponential backoff.

    Returns:
        Kết quả text nếu thành công, None nếu thất bại.
    """
    api_key = os.environ.get(tier.env_key, "").strip()
    if not api_key:
        print(f"  ⏭️  Bỏ qua [{tier.name}]: không tìm thấy API key ({tier.env_key})")
        return None

    for attempt in range(1, tier.max_retries + 1):
        try:
            if attempt > 1:
                wait = min(tier.backoff_base**attempt, tier.backoff_max)
                print(f"  ⏳ Đang chờ {wait:.0f}s trước khi thử lại...")
                time.sleep(wait)

            print(f"  🔄 [{tier.name}] Lần thử {attempt}/{tier.max_retries}...")
            result = _call_provider(tier, api_key, prompt)

            if result:
                print(f"  ✅ [{tier.name}] Phản hồi thành công!")
                return result
            else:
                print(f"  ⚠️  [{tier.name}] Phản hồi rỗng, thử lại...")

        except Exception as e:
            print(f"  ❌ [{tier.name}] Lỗi: {e}")

            if _is_permanent_error(e):
                print(f"  🚫 Lỗi vĩnh viễn → dừng retry tier này.")
                return None

            if not _is_retryable_error(e) and attempt >= 2:
                print(f"  🚫 Lỗi không xác định sau {attempt} lần → dừng retry.")
                return None

            if attempt == tier.max_retries:
                print(f"  💤 [{tier.name}] Đã hết {tier.max_retries} lần thử.")

    return None


# ============================================================
# HÀM CHÍNH: MULTI-TIER FAILOVER
# ============================================================


def generate_with_failover(prompt: str, task_label: str = "AI") -> str:
    """
    Gọi AI với hệ thống failover multi-tier.

    Duyệt qua các tier theo thứ tự ưu tiên. Mỗi tier có retry riêng
    với exponential backoff. Nếu tier hiện tại thất bại, tự động
    chuyển sang tier tiếp theo.

    Args:
        prompt: Nội dung prompt gửi đến AI.
        task_label: Nhãn mô tả tác vụ (để log rõ ràng hơn).

    Returns:
        Kết quả text từ AI.

    Raises:
        RuntimeError: Khi tất cả các tier đều thất bại.
    """
    print(f"\n  🤖 [{task_label}] Bắt đầu gọi AI (Multi-Tier Failover)")
    print(f"  {'─' * 50}")

    for i, tier in enumerate(TIERS, 1):
        tier_label = f"Tier {i}/{len(TIERS)}"
        print(f"\n  📡 {tier_label}: {tier.name} ({tier.provider})")

        result = _try_tier(tier, prompt)
        if result is not None:
            return result

        if i < len(TIERS):
            next_tier = TIERS[i]
            print(f"\n  🔀 Chuyển sang mô hình dự phòng: {next_tier.name}...")

    # Tất cả tier đều fail
    raise RuntimeError(
        f"[{task_label}] Tất cả {len(TIERS)} tier đều thất bại. "
        f"Kiểm tra API key và trạng thái dịch vụ."
    )


def clean_markdown_response(text: str) -> str:
    """Loại bỏ markdown code fences nếu AI lỡ sinh ra."""
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]  # Bỏ dòng đầu chứa ```
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]  # Bỏ dòng cuối
        text = "\n".join(lines).strip()
    return text
