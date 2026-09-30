import sqlite3
from typing import Any

from .config import get_db_path
from .db import initialize_database


def get_budget_for_month(month: str) -> dict[str, Any] | None:
    initialize_database()

    with sqlite3.connect(get_db_path()) as connection:
        row = connection.execute(
            "SELECT id, month, monthly_budget, currency, created_at, updated_at FROM budgets WHERE month = ?",
            (month,),
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "month": row[1],
        "monthly_budget": row[2],
        "currency": row[3],
        "created_at": row[4],
        "updated_at": row[5],
    }
