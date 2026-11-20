from __future__ import annotations

from .budget_repository import BudgetRepository
from .services import current_month_key, month_start, positive_amount


class BudgetService:
    def __init__(self, repository: BudgetRepository | None = None):
        self.repository = repository or BudgetRepository()

    @staticmethod
    def validate_amount(amount: float) -> float:
        return positive_amount(amount, "Budget")

    def get_current_budget(self) -> dict | None:
        return self.repository.get_by_month(current_month_key())

    def set_budget(self, amount: float, month: str | None = None) -> dict:
        validated_amount = self.validate_amount(amount)
        target_month = current_month_key() if month is None else month_start(month).isoformat()[:7]
        return self.repository.set_budget(target_month, validated_amount)
