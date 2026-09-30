from __future__ import annotations

from .budget_repository import BudgetRepository
from .services import current_month_key


class BudgetService:
    def __init__(self, repository: BudgetRepository | None = None):
        self.repository = repository or BudgetRepository()

    @staticmethod
    def validate_amount(amount: float) -> float:
        cleaned = float(amount)
        if cleaned <= 0:
            raise ValueError("Budget amount must be greater than 0.")
        return cleaned

    def get_current_budget(self) -> dict | None:
        return self.repository.get_by_month(current_month_key())

    def set_budget(self, amount: float, month: str | None = None) -> dict:
        validated_amount = self.validate_amount(amount)
        target_month = month or current_month_key()
        return self.repository.set_budget(target_month, validated_amount)
