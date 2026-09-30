from __future__ import annotations

from datetime import date

from .repositories import get_budget_for_month


def current_month_key() -> str:
    return date.today().strftime("%Y-%m")


def current_month_label() -> str:
    return date.today().strftime("%B %Y")


def get_dashboard_snapshot(month: str | None = None) -> dict:
    from .dashboard_service import DashboardService

    target_month = month or current_month_key()
    summary = DashboardService().get_monthly_summary(target_month)

    return {
        "month": summary["month"],
        "month_label": summary["month_label"],
        "budget_configured": summary["budget_configured"],
        "budget_amount": summary["budget"],
        "total_income": summary["total_income"],
        "monthly_budget": summary["budget"],
        "total_expenses": summary["total_expenses"],
        "required_expenses": summary["required_expenses"],
        "discretionary_expenses": summary["discretionary_expenses"],
        "expense_count": summary["expense_count"],
        "remaining_budget": summary["remaining_budget"],
        "budget_usage_percentage": summary["budget_usage_percentage"],
        "category_totals": summary["category_totals"],
        "recent_expenses": summary["recent_expenses"],
    }
