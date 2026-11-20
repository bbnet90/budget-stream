from __future__ import annotations

import calendar
from decimal import Decimal
from datetime import date

from .dashboard_repository import DashboardRepository
from .services import current_month_key


class DashboardService:
    def __init__(self, repository: DashboardRepository | None = None):
        self.repository = repository or DashboardRepository()

    def get_monthly_summary(self, month: str | None = None, today: date | None = None) -> dict:
        target_month = month or current_month_key(today)
        with self.repository.snapshot() as reader:
            expense_totals = reader.get_expense_totals_for_month(target_month)
            budget = reader.get_budget_for_month(target_month)
            expense_count = reader.get_expense_count_for_month(target_month)
            configured = reader.has_budget_for_month(target_month)
            income = reader.get_total_income_for_month(target_month)
            categories = reader.get_category_totals_for_month(target_month)
            recent = reader.get_recent_expenses_for_month(target_month, limit=5)
        remaining_budget = float(Decimal(str(budget)) - Decimal(str(expense_totals["total_expenses"])))
        days_remaining = self.get_days_remaining(target_month, today=today)
        budget_usage_percentage = 0.0 if budget == 0 else (expense_totals["total_expenses"] / budget) * 100
        daily_available = 0.0 if budget == 0 else remaining_budget / days_remaining

        return {
            "month": target_month,
            "month_label": self._month_label(target_month),
            "budget": budget,
            "budget_configured": configured,
            "total_income": income,
            "total_expenses": expense_totals["total_expenses"],
            "required_expenses": expense_totals["required_expenses"],
            "discretionary_expenses": expense_totals["discretionary_expenses"],
            "expense_count": expense_count,
            "remaining_budget": remaining_budget,
            "days_remaining": days_remaining,
            "daily_available": daily_available,
            "budget_usage_percentage": budget_usage_percentage,
            "category_totals": categories,
            "recent_expenses": recent,
        }

    @staticmethod
    def get_days_remaining(month: str, today: date | None = None) -> int:
        reference_day = today or date.today()
        year, month_number = map(int, month.split("-"))
        last_day = calendar.monthrange(year, month_number)[1]
        if (year, month_number) > (reference_day.year, reference_day.month):
            return last_day
        if (year, month_number) < (reference_day.year, reference_day.month):
            return 1
        days_remaining = (last_day - reference_day.day) + 1
        return max(1, days_remaining)

    @staticmethod
    def _month_label(month: str) -> str:
        try:
            from datetime import datetime

            return datetime.strptime(f"{month}-01", "%Y-%m-%d").strftime("%B %Y")
        except ValueError:
            return month
