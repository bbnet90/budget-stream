from __future__ import annotations

import calendar
from datetime import date

from .dashboard_repository import DashboardRepository
from .services import current_month_key


class DashboardService:
    def __init__(self, repository: DashboardRepository | None = None):
        self.repository = repository or DashboardRepository()

    def get_monthly_summary(self, month: str | None = None, today: date | None = None) -> dict:
        target_month = month or current_month_key()
        expense_totals = self.repository.get_expense_totals_for_month(target_month)
        budget = self.repository.get_budget_for_month(target_month)
        expense_count = self.repository.get_expense_count_for_month(target_month)
        remaining_budget = budget - expense_totals["total_expenses"]
        days_remaining = self.get_days_remaining(target_month, today=today)
        budget_usage_percentage = 0.0 if budget == 0 else (expense_totals["total_expenses"] / budget) * 100
        daily_available = 0.0 if budget == 0 else remaining_budget / days_remaining

        return {
            "month": target_month,
            "month_label": self._month_label(target_month),
            "budget": budget,
            "budget_configured": self.repository.has_budget_for_month(target_month),
            "total_income": self.repository.get_total_income_for_month(target_month),
            "total_expenses": expense_totals["total_expenses"],
            "required_expenses": expense_totals["required_expenses"],
            "discretionary_expenses": expense_totals["discretionary_expenses"],
            "expense_count": expense_count,
            "remaining_budget": remaining_budget,
            "days_remaining": days_remaining,
            "daily_available": daily_available,
            "budget_usage_percentage": budget_usage_percentage,
            "category_totals": self.repository.get_category_totals_for_month(target_month),
            "recent_expenses": self.repository.get_recent_expenses_for_month(target_month, limit=5),
        }

    @staticmethod
    def get_days_remaining(month: str, today: date | None = None) -> int:
        reference_day = today or date.today()
        year, month_number = map(int, month.split("-"))
        last_day = calendar.monthrange(year, month_number)[1]
        days_remaining = (last_day - reference_day.day) + 1
        return max(1, days_remaining)

    @staticmethod
    def _month_label(month: str) -> str:
        try:
            from datetime import datetime

            return datetime.strptime(f"{month}-01", "%Y-%m-%d").strftime("%B %Y")
        except ValueError:
            return month
