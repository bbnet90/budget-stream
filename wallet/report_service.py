from __future__ import annotations

from decimal import Decimal

from .dashboard_repository import DashboardRepository
from .services import current_month_key


class ReportService:
    def __init__(self, repository: DashboardRepository | None = None):
        self.repository = repository or DashboardRepository()

    def get_current_report(self, month: str | None = None) -> dict:
        target_month = month or current_month_key()
        with self.repository.snapshot() as reader:
            total_income = reader.get_total_income_for_month(target_month)
            expense_totals = reader.get_expense_totals_for_month(target_month)
            monthly_budget = reader.get_budget_for_month(target_month)
            category_totals = reader.get_category_totals_for_month(target_month)
        total_expenses = expense_totals["total_expenses"]
        remaining_budget = float(Decimal(str(monthly_budget)) - Decimal(str(total_expenses)))

        expense_to_income_percentage = 0.0 if total_income == 0 else (total_expenses / total_income) * 100
        required_share_percentage = 0.0 if total_expenses == 0 else (expense_totals["required_expenses"] / total_expenses) * 100
        discretionary_share_percentage = 0.0 if total_expenses == 0 else (expense_totals["discretionary_expenses"] / total_expenses) * 100
        budget_usage_percentage = 0.0 if monthly_budget == 0 else (total_expenses / monthly_budget) * 100

        ordered_categories = sorted(
            category_totals,
            key=lambda item: (-item["total"], item["category"]),
        )
        category_spending = []
        for item in ordered_categories:
            percentage = 0.0 if total_expenses == 0 else (item["total"] / total_expenses) * 100
            category_spending.append(
                {
                    "category": item["category"],
                    "amount": item["total"],
                    "percentage_of_total_expenses": round(percentage, 2),
                }
            )

        return {
            "income_vs_expense": {
                "total_income": total_income,
                "total_expenses": total_expenses,
                "net_cash_flow": float(Decimal(str(total_income)) - Decimal(str(total_expenses))),
                "expense_to_income_percentage": round(expense_to_income_percentage, 2),
            },
            "expense_breakdown": {
                "required_expenses": expense_totals["required_expenses"],
                "discretionary_expenses": expense_totals["discretionary_expenses"],
                "required_share_percentage": round(required_share_percentage, 2),
                "discretionary_share_percentage": round(discretionary_share_percentage, 2),
            },
            "budget_comparison": {
                "monthly_budget": monthly_budget,
                "total_expenses": total_expenses,
                "remaining_budget": remaining_budget,
                "budget_usage_percentage": round(budget_usage_percentage, 2),
            },
            "category_spending": category_spending,
        }
