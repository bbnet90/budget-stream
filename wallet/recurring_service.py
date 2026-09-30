from __future__ import annotations

from calendar import monthrange
from datetime import date

from wallet.budget_service import BudgetService
from wallet.db import get_connection
from wallet.expense_service import ExpenseService
from wallet.income_service import IncomeService
from wallet.recurring_repository import RecurringRepository


class RecurringService:
    def __init__(self):
        self.repository = RecurringRepository()

    def _parse_date(self, next_run_date: str | date) -> date:
        if isinstance(next_run_date, date):
            return next_run_date
        try:
            return date.fromisoformat(str(next_run_date))
        except ValueError as exc:
            raise ValueError("next_run_date must be a valid ISO date (YYYY-MM-DD).") from exc

    def _add_months(self, value: date, months: int = 1) -> date:
        year = value.year + (value.month - 1 + months) // 12
        month = (value.month - 1 + months) % 12 + 1
        last_day = monthrange(year, month)[1]
        day = min(value.day, last_day)
        return date(year, month, day)

    def _iter_due_dates(self, next_run_date: str | date, today: date) -> list[date]:
        start = self._parse_date(next_run_date)
        if start > today:
            return []

        occurrences: list[date] = []
        current = start
        while current <= today:
            occurrences.append(current)
            current = self._add_months(current, 1)
        return occurrences

    def _category_id_for_name(self, category_name: str | None) -> int | None:
        if category_name is None:
            return None
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM categories WHERE name = ?",
                (category_name,),
            ).fetchone()
        if row is None:
            raise ValueError(f"Category '{category_name}' does not exist.")
        return row["id"]

    def add_recurring(
        self,
        type_: str,
        amount: float,
        frequency: str = "monthly",
        next_run_date: str | date | None = None,
        source_name: str | None = None,
        category_name: str | None = None,
        description: str | None = None,
    ):
        recurring_type = str(type_).lower().strip()
        if recurring_type not in {"income", "expense"}:
            raise ValueError("Recurring type must be income or expense.")
        if amount <= 0:
            raise ValueError("Recurring amount must be greater than 0.")
        if str(frequency).lower() != "monthly":
            raise ValueError("Only monthly recurring transactions are supported.")
        if next_run_date is None:
            raise ValueError("next_run_date is required.")

        parsed_date = self._parse_date(next_run_date)
        if recurring_type == "income":
            if not source_name:
                raise ValueError("Income recurring entries require a source_name.")
            category_id = None
        else:
            if not category_name:
                raise ValueError("Expense recurring entries require a category_name.")
            category_id = self._category_id_for_name(category_name)
            source_name = None

        return self.repository.add_recurring(
            type_=recurring_type,
            source_name=source_name,
            category_id=category_id,
            amount=float(amount),
            description=description,
            frequency="monthly",
            next_run_date=parsed_date.isoformat(),
            is_active=1,
        )

    def list_recurring(self):
        items = self.repository.list_all()
        return sorted(items, key=lambda item: (item["next_run_date"], item["id"]))

    def get_recurring_by_id(self, recurring_id: int):
        return self.repository.get_by_id(recurring_id)

    def enable_recurring(self, recurring_id: int):
        return self.repository.update_status(recurring_id, 1)

    def disable_recurring(self, recurring_id: int):
        return self.repository.update_status(recurring_id, 0)

    def delete_recurring(self, recurring_id: int):
        self.repository.delete_by_id(recurring_id)

    def apply_due_recurring(self, today: date | None = None):
        reference_day = today or date.today()
        due_entries = self.repository.get_active_due(reference_day.isoformat())
        results = []

        for recurring in due_entries:
            due_dates = self._iter_due_dates(recurring["next_run_date"], reference_day)
            if not due_dates:
                continue

            last_due_date = due_dates[-1]
            for due_date in due_dates:
                if recurring["type"] == "income":
                    created = IncomeService().add_income(
                        source_name=recurring["source_name"],
                        amount=recurring["amount"],
                        month=due_date.strftime("%Y-%m"),
                    )
                else:
                    category_name = recurring["category_name"]
                    if not category_name:
                        raise ValueError("Expense recurring entries must include a category.")
                    created = ExpenseService().add_expense(
                        amount=recurring["amount"],
                        category_name=category_name,
                        description=recurring["description"] or "Recurring expense",
                        expense_date=due_date.isoformat(),
                    )

                results.append(
                    {
                        "id": recurring["id"],
                        "type": recurring["type"],
                        "source_name": recurring["source_name"],
                        "category_name": recurring["category_name"],
                        "amount": recurring["amount"],
                        "due_date": due_date.isoformat(),
                        "created": created,
                    }
                )

            next_run_date = self._add_months(last_due_date, 1).isoformat()
            self.repository.update_next_run_date(recurring["id"], next_run_date)

        return results


__all__ = ["RecurringService"]
