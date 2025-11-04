from __future__ import annotations

from typing import Iterable

from .models import AnalysisSummary, CategoryAnalysis, PurchaseItem
from .utils import unique_preserve_order


def _format_amount(value: float) -> str:
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def build_summary(
    detected_categories: Iterable[str],
    enough: Iterable[CategoryAnalysis],
    shortage: Iterable[CategoryAnalysis],
    unmatched: Iterable[PurchaseItem],
) -> AnalysisSummary:
    detected_names = unique_preserve_order(detected_categories)

    lines: list[str] = []
    if detected_names:
        lines.append("В договоре определены следующие товарные группы:")
        for name in detected_names:
            lines.append(f"- {name}")
    else:
        lines.append("В договоре не удалось определить товарные группы.")

    if enough:
        lines.append("")
        lines.append("Средств хватает:")
        for category in enough:
            lines.append(
                f"{category.category}: нужно {_format_amount(category.needed)} доступно {_format_amount(category.available)}"
            )

    if shortage:
        lines.append("")
        lines.append("Средств не хватает:")
        for category in shortage:
            lines.append(
                f"{category.category}: нужно {_format_amount(category.needed)} доступно {_format_amount(category.available)}"
            )

    if unmatched:
        lines.append("")
        lines.append("Не удалось сопоставить категории для следующих позиций:")
        for item in unmatched:
            lines.append(f"- {item.name} ({_format_amount(item.amount)})")

    message = "\n".join(lines)
    return AnalysisSummary(
        categories_detected=detected_names,
        enough=list(enough),
        shortage=list(shortage),
        unmatched_items=list(unmatched),
        message=message,
    )
