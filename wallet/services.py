from __future__ import annotations

from datetime import date
from math import isfinite

from .repositories import get_budget_for_month


def positive_amount(amount: float, label: str) -> float:
    value = float(amount)
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{label} amount must be finite and greater than 0.")
    return value


def month_start(month: str) -> date:
    try:
        return date.fromisoformat(f"{month}-01")
    except ValueError as exc:
        raise ValueError("Month must be a valid calendar month (YYYY-MM).") from exc


def current_month_key(today: date | None = None) -> str:
    return (today or date.today()).isoformat()[:7]


def current_month_label() -> str:
    return date.today().strftime("%B %Y")


def get_dashboard_snapshot(month: str | None = None) -> dict:
    from .dashboard_service import DashboardService

    summary = DashboardService().get_monthly_summary(month)
    budget = summary.pop("budget")
    return {**summary, "budget_amount": budget, "monthly_budget": budget}
