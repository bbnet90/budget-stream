from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime

from wallet.db import database_session
from wallet.expense_service import ExpenseService
from wallet.income_service import IncomeService
from wallet.recurring_repository import RecurringRepository
from wallet.services import positive_amount


class RecurringService:
    def __init__(self):
        self.repository = RecurringRepository()

    @staticmethod
    def _parse_date(next_run_date: str | date) -> date:
        if isinstance(next_run_date, datetime):
            return next_run_date.date()
        if isinstance(next_run_date, date):
            return next_run_date
        try:
            return date.fromisoformat(str(next_run_date))
        except ValueError as exc:
            raise ValueError("next_run_date must be a valid ISO date (YYYY-MM-DD).") from exc

    @staticmethod
    def _next_month(value: date) -> date:
        year = value.year + value.month // 12
        month = value.month % 12 + 1
        return date(year, month, min(value.day, monthrange(year, month)[1]))

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
        amount = positive_amount(amount, "Recurring")
        if str(frequency).lower() != "monthly":
            raise ValueError("Only monthly recurring transactions are supported.")
        if next_run_date is None:
            raise ValueError("next_run_date is required.")

        parsed_date = self._parse_date(next_run_date)
        if recurring_type == "income":
            source_name = IncomeService.validate_source(source_name or "")
            category_id = None
        else:
            if not category_name:
                raise ValueError("Expense recurring entries require a category_name.")
            category_id = ExpenseService().get_category(category_name)["id"]
            description = ExpenseService.normalize_description(description)
            source_name = None

        return self.repository.add_recurring(
            type_=recurring_type,
            source_name=source_name,
            category_id=category_id,
            amount=amount,
            description=description,
            frequency="monthly",
            next_run_date=parsed_date.isoformat(),
        )

    def list_recurring(self):
        return self.repository.list_all()

    def get_recurring_by_id(self, recurring_id: int):
        return self.repository.get_by_id(recurring_id)

    def _set_active(self, recurring_id: int, is_active: int):
        entry = self.repository.update_status(recurring_id, is_active)
        if entry is None:
            raise ValueError(f"Recurring transaction with id {recurring_id} does not exist.")
        return entry

    def enable_recurring(self, recurring_id: int):
        return self._set_active(recurring_id, 1)

    def disable_recurring(self, recurring_id: int):
        return self._set_active(recurring_id, 0)

    def delete_recurring(self, recurring_id: int):
        if not self.repository.delete_by_id(recurring_id):
            raise ValueError(f"Recurring transaction with id {recurring_id} does not exist.")

    def apply_due_recurring(self, today: date | None = None):
        reference_day = today or date.today()
        results = []
        with database_session() as conn:
            # Acquire the writer lock before reading schedules so concurrent applies see committed dates.
            conn.execute("BEGIN IMMEDIATE")
            for recurring in self.repository.get_active_due(reference_day.isoformat(), conn):
                due = self._parse_date(recurring["next_run_date"])
                due_dates = []
                while due <= reference_day:
                    due_dates.append(due.isoformat())
                    due = self._next_month(due)
                created_entries = self.repository.apply_occurrences(recurring, due_dates, due.isoformat(), conn)
                results.extend(
                    {
                        "id": recurring["id"],
                        "type": recurring["type"],
                        "source_name": recurring["source_name"],
                        "category_name": recurring["category_name"],
                        "amount": recurring["amount"],
                        "due_date": due_date,
                        "created": created,
                    }
                    for due_date, created in zip(due_dates, created_entries)
                )
        return results


__all__ = ["RecurringService"]
