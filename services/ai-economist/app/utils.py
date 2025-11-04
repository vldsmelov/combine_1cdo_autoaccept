from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Iterable

WHITESPACE_RE = re.compile(r"\s+")
NON_WORD_RE = re.compile(r"[^a-zA-Zа-яА-Я0-9]+", re.UNICODE)


def normalize_text(value: str) -> str:
    """Lowercase string normalization used for matching categories and items."""
    value = value.lower()
    value = value.replace("ё", "е")
    value = NON_WORD_RE.sub(" ", value)
    value = WHITESPACE_RE.sub(" ", value)
    return value.strip()


def parse_money(value: float | int | str | Decimal | None) -> float:
    """Parse a numeric input that may contain spaces or commas."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace("\xa0", " ")
        cleaned = cleaned.replace(" ", "")
        cleaned = cleaned.replace(",", ".")
        if not cleaned:
            return 0.0
        try:
            return float(Decimal(cleaned))
        except (InvalidOperation, ValueError):
            raise ValueError(f"Cannot parse monetary value: {value!r}")
    raise TypeError(f"Unsupported type for money parsing: {type(value)!r}")


def unique_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered
