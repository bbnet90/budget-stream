from __future__ import annotations

from .income_repository import IncomeRepository
from .services import current_month_key


class IncomeService:
    def __init__(self, repository: IncomeRepository | None = None):
        self.repository = repository or IncomeRepository()

    @staticmethod
    def validate_source(source_name: str) -> str:
        cleaned = (source_name or "").strip()
        if not cleaned:
            raise ValueError("Income source name is required.")
        return cleaned

    @staticmethod
    def validate_amount(amount: float) -> float:
        cleaned = float(amount)
        if cleaned <= 0:
            raise ValueError("Income amount must be greater than 0.")
        return cleaned

    def add_income(self, source_name: str, amount: float, month: str | None = None) -> dict:
        cleaned_source = self.validate_source(source_name)
        validated_amount = self.validate_amount(amount)
        target_month = month or current_month_key()
        return self.repository.add_income(target_month, cleaned_source, validated_amount)

    def list_current_month_income(self) -> list[dict]:
        return self.repository.list_by_month(current_month_key())
