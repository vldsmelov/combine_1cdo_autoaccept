from __future__ import annotations

from typing import Dict

from .models import Budget, BudgetRequest, BudgetResponse, merge_category_inputs


class BudgetStorage:
    """In-memory storage for uploaded budgets."""

    def __init__(self) -> None:
        self._budgets: Dict[str, Budget] = {}

    def upsert_budget(self, payload: BudgetRequest) -> BudgetResponse:
        categories = merge_category_inputs(payload.categories)
        budget = BudgetResponse(budget_id=payload.budget_id, categories=categories)
        self._budgets[payload.budget_id] = budget
        return budget

    def get_budget(self, budget_id: str) -> Budget:
        budget = self._budgets.get(budget_id)
        if not budget:
            raise KeyError(budget_id)
        return budget

    def list_budget_ids(self) -> list[str]:
        return list(self._budgets.keys())


storage = BudgetStorage()
