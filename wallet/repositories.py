from typing import Any

from .budget_repository import BudgetRepository
from .db import initialize_database


def get_budget_for_month(month: str) -> dict[str, Any] | None:
    initialize_database()
    return BudgetRepository().get_by_month(month)
