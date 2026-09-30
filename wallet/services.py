from __future__ import annotations

from datetime import date

from .repositories import get_budget_for_month


def current_month_key() -> str:
    return date.today().strftime("%Y-%m")


def current_month_label() -> str:
    return date.today().strftime("%B %Y")


def get_dashboard_snapshot(month: str | None = None) -> dict:
    target_month = month or current_month_key()
    budget = get_budget_for_month(target_month)

    month_label = date.fromisoformat(f"{target_month}-01").strftime("%B %Y")

    if budget is None:
        return {
            "month": target_month,
            "month_label": month_label,
            "budget_configured": False,
            "budget_amount": None,
        }

    return {
        "month": target_month,
        "month_label": month_label,
        "budget_configured": True,
        "budget_amount": budget["monthly_budget"],
    }
