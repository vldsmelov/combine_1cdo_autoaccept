from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .budget_store import storage
from .matcher import matcher
from .models import (
    AnalysisRequest,
    AnalysisResponse,
    BudgetRequest,
    BudgetResponse,
    CategoryAnalysis,
    PurchaseItem,
)
from .summary import build_summary

app = FastAPI(
    title="AI Economist",
    description="Сервис экономического контроля бюджетов",
    version="0.1.0",
)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/budget", response_model=list[str])
def list_budgets() -> list[str]:
    return storage.list_budget_ids()


@app.post("/budget", response_model=BudgetResponse)
def upsert_budget(payload: BudgetRequest) -> BudgetResponse:
    budget = storage.upsert_budget(payload)
    return budget


@app.get("/budget/{budget_id}", response_model=BudgetResponse)
def get_budget(budget_id: str) -> BudgetResponse:
    try:
        budget = storage.get_budget(budget_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Budget {budget_id} not found") from exc
    return budget


@app.post("/analyze", response_model=AnalysisResponse)
def analyze(request: AnalysisRequest) -> AnalysisResponse:
    try:
        budget = storage.get_budget(request.budget_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Budget {request.budget_id} not found") from exc

    matched_categories: dict[str, CategoryAnalysis] = {}
    unmatched: list[PurchaseItem] = []

    for item in request.items:
        result = matcher.match(item, budget.categories)
        if result.category is None:
            unmatched.append(item)
            continue
        category_name = result.category.name
        existing = matched_categories.get(category_name)
        if existing is None:
            matched_categories[category_name] = CategoryAnalysis(
                category=category_name,
                needed=item.amount,
                available=result.category.available,
                enough=item.amount <= result.category.available,
                items=[item],
            )
        else:
            existing.items.append(item)
            existing.needed += item.amount
            existing.enough = existing.needed <= existing.available

    details = list(matched_categories.values())
    enough = [category for category in details if category.enough]
    shortage = [category for category in details if not category.enough]

    summary = build_summary(
        detected_categories=(category.category for category in details),
        enough=enough,
        shortage=shortage,
        unmatched=unmatched,
    )

    return AnalysisResponse(budget_id=budget.budget_id, summary=summary, details=details)
