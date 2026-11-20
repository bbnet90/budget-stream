from __future__ import annotations

from datetime import date
import sqlite3

from .category_repository import CategoryRepository
from .expense_repository import ExpenseRepository
from .services import current_month_key, positive_amount


class ExpenseService:
    def __init__(
        self,
        repository: ExpenseRepository | None = None,
        category_repository: CategoryRepository | None = None,
    ):
        self.repository = repository or ExpenseRepository()
        self.category_repository = category_repository or CategoryRepository(self.repository.db_path)

    @staticmethod
    def validate_amount(amount: float) -> float:
        return positive_amount(amount, "Expense")

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

        try:
            day = date.fromisoformat(expense_date) if expense_date is not None else date.today()
        except ValueError as exc:
            raise ValueError("Expense date must be a valid calendar date (YYYY-MM-DD).") from exc

        if is_required is None:
            is_required = category["kind"] == "required"

        try:
            return self.repository.add_expense(
                category_id=category["id"],
                amount=validated_amount,
                description=cleaned_description,
                expense_date=day.isoformat(),
                is_required=int(bool(is_required)),
            )
        except sqlite3.IntegrityError as exc:
            if exc.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_FOREIGNKEY:
                raise ValueError(f'Category "{category_name}" does not exist.') from exc
            raise

    def list_current_month_expenses(self) -> list[dict]:
        return self.repository.list_by_month(current_month_key())

    def delete_expense(self, expense_id: int) -> bool:
        if not self.repository.delete_by_id(expense_id):
            raise ValueError(f"Expense with id {expense_id} does not exist.")
        return True
