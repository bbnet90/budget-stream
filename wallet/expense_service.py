from __future__ import annotations

from datetime import date

from .category_repository import CategoryRepository
from .expense_repository import ExpenseRepository
from .services import current_month_key


class ExpenseService:
    def __init__(
        self,
        repository: ExpenseRepository | None = None,
        category_repository: CategoryRepository | None = None,
    ):
        self.repository = repository or ExpenseRepository()
        self.category_repository = category_repository or CategoryRepository()

    @staticmethod
    def validate_amount(amount: float) -> float:
        cleaned = float(amount)
        if cleaned <= 0:
            raise ValueError("Expense amount must be greater than 0.")
        return cleaned

    @staticmethod
    def normalize_description(description: str | None) -> str | None:
        if description is None:
            return None

        cleaned = description.strip()
        return cleaned or None

    def get_category(self, category_name: str) -> dict:
        cleaned = (category_name or "").strip()
        if not cleaned:
            raise ValueError("Category is required.")

        category = self.category_repository.get_category_by_name(cleaned)
        if category is None:
            raise ValueError(f'Category "{cleaned}" does not exist.')

        return category

    def add_expense(
        self,
        amount: float,
        category_name: str,
        description: str | None = None,
        expense_date: str | None = None,
        is_required: bool | None = None,
    ) -> dict:
        validated_amount = self.validate_amount(amount)
        category = self.get_category(category_name)
        cleaned_description = self.normalize_description(description)

        if expense_date is None:
            expense_date = date.today().strftime("%Y-%m-%d")

        if is_required is None:
            is_required = category["kind"] == "required"

        saved = self.repository.add_expense(
            category_id=category["id"],
            amount=validated_amount,
            description=cleaned_description,
            expense_date=expense_date,
            is_required=int(bool(is_required)),
        )

        if saved is None:
            raise ValueError("Expense could not be saved.")

        return saved

    def list_current_month_expenses(self) -> list[dict]:
        return self.repository.list_by_month(current_month_key())

    def delete_expense(self, expense_id: int) -> bool:
        existing = self.repository.get_by_id(expense_id)
        if existing is None:
            raise ValueError(f"Expense with id {expense_id} does not exist.")

        self.repository.delete_by_id(expense_id)
        return True
