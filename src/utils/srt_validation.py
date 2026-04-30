"""
Small SRT structure validator used after AI subtitle edits.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


_BLOCK_SEPARATOR_RE = re.compile(r"\n\s*\n")
_TIMESTAMP_RE = re.compile(
    r"^\d{2}:\d{2}:\d{2},\d{3}\s+-->\s+\d{2}:\d{2}:\d{2},\d{3}(?:\s+.*)?$"
)


class SrtValidationError(ValueError):
    """Raised when an AI-generated SRT no longer matches the source structure."""


@dataclass(frozen=True)
class SrtBlock:
    index: str
    timestamp: str
    text_lines: tuple[str, ...]


@dataclass(frozen=True)
class SrtCoercionResult:
    text: str
    repaired_indices: int
    repaired_timestamps: int


def normalize_srt_text(text: str) -> str:
    """Normalize line endings and ensure the SRT text ends with one newline."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return ""
    return normalized + "\n"


def parse_srt_structure(text: str, label: str = "SRT") -> list[SrtBlock]:
    """
    Parse enough SRT structure to validate AI output safely.

    This intentionally keeps the parser strict: invalid or extra non-SRT text should
    fail before the text is written to the next pipeline step.
    """
    normalized = normalize_srt_text(text)
    if not normalized:
        raise SrtValidationError(f"{label}: empty SRT content.")

    raw_blocks = [
        block for block in _BLOCK_SEPARATOR_RE.split(normalized.strip()) if block.strip()
    ]
    if not raw_blocks:
        raise SrtValidationError(f"{label}: no subtitle blocks found.")

    blocks: list[SrtBlock] = []
    errors: list[str] = []

    for block_no, raw_block in enumerate(raw_blocks, 1):
        lines = [line.rstrip() for line in raw_block.split("\n")]

        if len(lines) < 3:
            errors.append(
                f"block {block_no}: expected index, timestamp, and subtitle text."
            )
            continue

        index = lines[0].strip()
        timestamp = lines[1].strip()
        text_lines = tuple(lines[2:])

        if not index.isdigit():
            errors.append(f"block {block_no}: invalid index line {index!r}.")
        if not _TIMESTAMP_RE.match(timestamp):
            errors.append(f"block {block_no}: invalid timestamp line {timestamp!r}.")
        if not any(line.strip() for line in text_lines):
            errors.append(f"block {block_no}: empty subtitle text.")

        blocks.append(SrtBlock(index=index, timestamp=timestamp, text_lines=text_lines))

    if errors:
        preview = "\n".join(f"- {err}" for err in errors[:10])
        remaining = len(errors) - 10
        if remaining > 0:
            preview += f"\n- ... and {remaining} more error(s)"
        raise SrtValidationError(f"{label}: invalid SRT structure:\n{preview}")

    return blocks


def _format_srt_blocks(blocks: list[SrtBlock]) -> str:
    rendered_blocks: list[str] = []
    for block in blocks:
        rendered_blocks.append(
            "\n".join((block.index, block.timestamp, *block.text_lines))
        )
    return "\n\n".join(rendered_blocks) + "\n"


def validate_srt_structure(
    reference_text: str,
    candidate_text: str,
    task_label: str = "AI SRT output",
) -> None:
    """
    Ensure AI output preserves block count, index lines, timestamps, and order.
    """
    reference_blocks = parse_srt_structure(reference_text, "reference SRT")
    candidate_blocks = parse_srt_structure(candidate_text, task_label)

    errors: list[str] = []

    if len(candidate_blocks) != len(reference_blocks):
        errors.append(
            "block count changed: "
            f"expected {len(reference_blocks)}, got {len(candidate_blocks)}."
        )

    for pos, (expected, actual) in enumerate(
        zip(reference_blocks, candidate_blocks), 1
    ):
        if actual.index != expected.index:
            errors.append(
                f"block {pos}: index changed from {expected.index!r} to {actual.index!r}."
            )
        if actual.timestamp != expected.timestamp:
            errors.append(
                "block "
                f"{pos}: timestamp changed from {expected.timestamp!r} "
                f"to {actual.timestamp!r}."
            )

    if errors:
        preview = "\n".join(f"- {err}" for err in errors[:10])
        remaining = len(errors) - 10
        if remaining > 0:
            preview += f"\n- ... and {remaining} more error(s)"
        raise SrtValidationError(f"{task_label}: SRT structure changed:\n{preview}")


def coerce_validated_srt(
    reference_text: str,
    candidate_text: str,
    task_label: str = "AI SRT output",
) -> str:
    """Validate candidate SRT and return it with normalized line endings."""
    return coerce_srt_to_reference_structure(
        reference_text,
        candidate_text,
        task_label,
    ).text


def coerce_srt_to_reference_structure(
    reference_text: str,
    candidate_text: str,
    task_label: str = "AI SRT output",
) -> SrtCoercionResult:
    """
    Keep AI-edited subtitle text but force index/timestamp lines from reference.

    This fixes common AI mistakes such as changing `00:04:12,659` into
    `00:14:12,659` while still failing hard if the AI merged, split, removed, or
    added subtitle blocks.
    """
    reference_blocks = parse_srt_structure(reference_text, "reference SRT")
    candidate_blocks = parse_srt_structure(candidate_text, task_label)

    if len(candidate_blocks) != len(reference_blocks):
        raise SrtValidationError(
            f"{task_label}: block count changed: expected "
            f"{len(reference_blocks)}, got {len(candidate_blocks)}."
        )

    repaired_indices = 0
    repaired_timestamps = 0
    coerced_blocks: list[SrtBlock] = []

    for expected, actual in zip(reference_blocks, candidate_blocks):
        if actual.index != expected.index:
            repaired_indices += 1
        if actual.timestamp != expected.timestamp:
            repaired_timestamps += 1

        coerced_blocks.append(
            SrtBlock(
                index=expected.index,
                timestamp=expected.timestamp,
                text_lines=actual.text_lines,
            )
        )

    return SrtCoercionResult(
        text=_format_srt_blocks(coerced_blocks),
        repaired_indices=repaired_indices,
        repaired_timestamps=repaired_timestamps,
    )
