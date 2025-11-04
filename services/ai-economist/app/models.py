from __future__ import annotations

from typing import Iterable

from pydantic import BaseModel, Field, computed_field, model_validator

from .utils import normalize_text, parse_money, unique_preserve_order


class BudgetCategoryInput(BaseModel):
    name: str = Field(..., min_length=1, description="Название категории бюджета")
    limit: float | None = Field(
        default=None,
        description="Первоначальный лимит. Если не задан, используется только доступная сумма.",
        ge=0,
    )
    reserved: float | None = Field(default=None, description="Зарезервированная сумма", ge=0)
    spent: float | None = Field(default=None, description="Уже оплачено", ge=0)
    available: float | None = Field(
        default=None,
        description="Доступная сумма. Если не задано, будет вычислено по формуле limit - reserved - spent",
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_numbers(cls, data: dict) -> dict:
        numeric_fields = ["limit", "reserved", "spent", "available"]
        for field in numeric_fields:
            if field in data and data[field] is not None:
                data[field] = parse_money(data[field])
        return data

    @model_validator(mode="after")
    def _ensure_available(self) -> "BudgetCategoryInput":
        if self.available is not None:
            return self
        limit = self.limit or 0.0
        reserved = self.reserved or 0.0
        spent = self.spent or 0.0
        available = limit - reserved - spent
        self.available = max(available, 0.0)
        return self


class BudgetCategory(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list, description="Все встреченные названия категории")
    limit: float | None = None
    reserved: float = 0.0
    spent: float = 0.0
    available: float = 0.0

    @model_validator(mode="before")
    @classmethod
    def _normalize_numbers(cls, data: dict) -> dict:
        for key in ("limit", "reserved", "spent", "available"):
            if key in data and data[key] is not None:
                data[key] = parse_money(data[key])
        return data

    @computed_field
    @property
    def normalized_name(self) -> str:
        return normalize_text(self.name)


class Budget(BaseModel):
    budget_id: str = Field(..., min_length=1)
    categories: list[BudgetCategory]

    @computed_field
    @property
    def normalized_categories(self) -> dict[str, BudgetCategory]:
        return {category.normalized_name: category for category in self.categories}


class BudgetRequest(BaseModel):
    budget_id: str
    categories: list[BudgetCategoryInput]


class BudgetResponse(Budget):
    pass


class PurchaseItem(BaseModel):
    name: str
    amount: float = Field(..., gt=0)
    description: str | None = None
    quantity: float | None = Field(default=None, gt=0)

    @model_validator(mode="before")
    @classmethod
    def _normalize_numbers(cls, data: dict) -> dict:
        if "amount" in data:
            data["amount"] = parse_money(data["amount"])
        if "quantity" in data and data["quantity"] is not None:
            data["quantity"] = parse_money(data["quantity"])
        return data

    @computed_field
    @property
    def full_text(self) -> str:
        parts = [self.name]
        if self.description:
            parts.append(self.description)
        return " ".join(parts)


class AnalysisRequest(BaseModel):
    budget_id: str
    items: list[PurchaseItem]


class ItemBreakdown(BaseModel):
    item: PurchaseItem
    matched_category: str | None = None


class CategoryAnalysis(BaseModel):
    category: str
    needed: float
    available: float
    enough: bool
    items: list[PurchaseItem]


class AnalysisSummary(BaseModel):
    categories_detected: list[str]
    enough: list[CategoryAnalysis]
    shortage: list[CategoryAnalysis]
    unmatched_items: list[PurchaseItem]
    message: str


class AnalysisResponse(BaseModel):
    budget_id: str
    summary: AnalysisSummary
    details: list[CategoryAnalysis]


def merge_category_inputs(inputs: Iterable[BudgetCategoryInput]) -> list[BudgetCategory]:
    buckets: dict[str, BudgetCategory] = {}
    aliases: dict[str, list[str]] = {}
    for category in inputs:
        normalized = normalize_text(category.name)
        bucket = buckets.get(normalized)
        if bucket is None:
            buckets[normalized] = BudgetCategory(
                name=category.name.strip(),
                aliases=[category.name.strip()],
                limit=category.limit,
                reserved=category.reserved or 0.0,
                spent=category.spent or 0.0,
                available=category.available or 0.0,
            )
        else:
            bucket.available += category.available or 0.0
            if category.limit is not None:
                bucket.limit = (bucket.limit or 0.0) + category.limit
            bucket.reserved += category.reserved or 0.0
            bucket.spent += category.spent or 0.0
            bucket.aliases.append(category.name.strip())
        aliases.setdefault(normalized, []).append(category.name.strip())
    # normalize alias lists
    for normalized, bucket in buckets.items():
        alias_list = aliases.get(normalized, [])
        bucket.aliases = unique_preserve_order(alias_list)
        if bucket.limit is not None:
            bucket.limit = max(bucket.limit, bucket.available + bucket.reserved + bucket.spent)
    return list(buckets.values())
