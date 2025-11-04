from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping

from .models import BudgetCategory, PurchaseItem
from .utils import normalize_text

DEFAULT_SYNONYMS: Mapping[str, set[str]] = {
    "благотворительная помощь": {"благотвор", "пожертв"},
    "спонсорство": {"спонсор"},
    "информационно консультационные услуги": {"консалт", "информацион", "консультац"},
    "командировочные расходы": {"командиров", "проезд", "гостиниц"},
    "материалы": {"материал", "сырье", "комплект"},
    "материалы для испытаний": {"испыт"},
    "мебель": {"мебель", "стол", "стул", "шкаф", "офисн"},
    "обслуживание программного обеспечения": {"обслуживание по", "сопровожден", "support"},
    "услуги по обслуживанию программного обеспечения": {"сопровожден", "обновлени", "администрирован"},
    "обучение": {"обуч", "семинар", "тренинг", "повышение квалификац"},
    "оргтехника": {"оргтех", "принтер", "копир", "сканер", "мфу", "плоттер"},
    "оргтехника стоимостью менее 100 тыс руб": {"оргтехника", "100", "меньше 100"},
    "оргтехника до 100 тыс": {"оргтехника", "100", "до 100"},
    "подписка на периодические издания": {"подписк", "журнал", "издан"},
    "литература": {"книга", "литератур", "учебник"},
    "поставка питьевой воды": {"вода", "питьев", "бутыль"},
    "продукты питания": {"питани", "продукт", "кейтеринг", "еда"},
    "посуда и приборы текстиль кухонный инвентарь": {"посуда", "текстиль", "кухон"},
    "хозяйственный инвентарь": {"инвентар", "уборк", "моющ"},
    "представительские расходы": {"представ", "делов", "прием"},
    "приборы и оборудование стоимостью менее 100 тыс руб": {"оборуд", "прибор", "100"},
    "приборы оборудование стоимостью менее 40 тыс руб": {"оборуд", "прибор", "40"},
    "оборудование до 40 тысяч": {"оборуд", "40"},
    "приобретение неисключительных прав лицензии": {"лиценз", "неисключ", "прав"},
    "программное обеспечение": {"по", "software", "программ"},
    "резерв": {"резерв"},
    "ремонт зданий сооружений": {"ремонт", "здан", "сооруж", "помещ"},
    "штрафы и пени": {"штраф", "пен"},
    "электроника": {"электрон", "компьют", "ноутбук", "монитор"},
    "крупная бытовая техника": {"бытов", "холодил", "стирал", "плита"},
}


@dataclass
class MatchResult:
    category: BudgetCategory | None
    reason: str | None


class CategoryMatcher:
    """Heuristically assign purchase items to budget categories."""

    def __init__(self, synonyms: Mapping[str, Iterable[str]] | None = None) -> None:
        self.synonyms: Dict[str, set[str]] = {
            normalize_text(key): {normalize_text(v) for v in values}
            for key, values in (synonyms or DEFAULT_SYNONYMS).items()
        }

    def match(self, item: PurchaseItem, categories: Iterable[BudgetCategory]) -> MatchResult:
        normalized_text = normalize_text(item.full_text)
        best_match: MatchResult = MatchResult(category=None, reason=None)

        # 1. Direct category name match
        for category in categories:
            normalized_name = category.normalized_name
            if normalized_name and normalized_name in normalized_text:
                return MatchResult(category=category, reason="name")

        # 2. Keyword match
        for category in categories:
            normalized_name = category.normalized_name
            keywords = self.synonyms.get(normalized_name, set())
            if not keywords and normalized_name:
                keywords = {word for word in normalized_name.split(" ") if len(word) > 3}
            for keyword in keywords:
                if keyword and keyword in normalized_text:
                    return MatchResult(category=category, reason="keyword")

        # 3. Fallback: longest overlapping word with any category name
        tokens = normalized_text.split()
        for category in categories:
            name_tokens = category.normalized_name.split()
            overlap = set(tokens) & set(name_tokens)
            if overlap:
                if best_match.category is None or len(overlap) > len(
                    best_match.category.normalized_name.split()
                ):
                    best_match = MatchResult(category=category, reason="overlap")

        return best_match


matcher = CategoryMatcher()
