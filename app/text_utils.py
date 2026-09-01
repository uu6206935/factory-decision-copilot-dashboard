from __future__ import annotations

from pathlib import Path


def repair_utf8_as_cp932(value: str) -> str:
    """Repair the common Windows mojibake: UTF-8 bytes decoded as CP932/Shift-JIS.

    Example: 品質検査結果 -> 蜩∬ｳｪ讀懈渊邨先棡.  Legitimate Japanese text is
    left untouched because it normally cannot round-trip through this inverse transform.
    """
    text = str(value or "")
    try:
        repaired = text.encode("cp932").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    if repaired == text:
        return text
    # Only accept a repair that produces Japanese/CJK characters and removes typical
    # mojibake punctuation/half-width artifacts rather than changing arbitrary names.
    has_japanese = any(
        "\u3040" <= ch <= "\u30ff" or "\u3400" <= ch <= "\u9fff"
        for ch in repaired
    )
    suspicious_before = sum(ch in "∬ｳｪ渊棡髫縺繧譁蜩讀邨" or 0xFF61 <= ord(ch) <= 0xFF9F for ch in text)
    suspicious_after = sum(ch in "∬ｳｪ渊棡髫縺繧譁蜩讀邨" or 0xFF61 <= ord(ch) <= 0xFF9F for ch in repaired)
    if has_japanese and suspicious_before > suspicious_after:
        return repaired
    return text


def display_filename(name: str) -> str:
    return repair_utf8_as_cp932(name)


def resolve_source_path(data_dir: Path, display_name: str) -> Path | None:
    direct = next((p for p in data_dir.rglob(display_name) if p.is_file()), None)
    if direct is not None:
        return direct
    return next((p for p in data_dir.rglob("*") if p.is_file() and display_filename(p.name) == display_name), None)
