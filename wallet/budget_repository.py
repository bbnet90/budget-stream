import sqlite3
from typing import Any

from .config import get_db_path


class BudgetRepository:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(get_db_path())

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def get_by_month(self, month: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, month, monthly_budget, currency, created_at, updated_at FROM budgets WHERE month = ?",
                (month,),
            ).fetchone()

        if row is None:
            return None

        return {
            "id": row["id"],
            "month": row["month"],
            "monthly_budget": row["monthly_budget"],
            "currency": row["currency"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def set_budget(self, month: str, amount: float) -> dict[str, Any]:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO budgets (month, monthly_budget, currency)
                VALUES (?, ?, 'TRY')
                ON CONFLICT(month) DO UPDATE SET
                    monthly_budget = excluded.monthly_budget,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (month, amount),
            )
            connection.commit()

        budget_id = cursor.lastrowid or self.get_by_month(month)["id"]
        return self.get_by_id(budget_id)

    def get_by_id(self, budget_id: int) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, month, monthly_budget, currency, created_at, updated_at FROM budgets WHERE id = ?",
                (budget_id,),
            ).fetchone()

        if row is None:
            return None

        return {
            "id": row["id"],
            "month": row["month"],
            "monthly_budget": row["monthly_budget"],
            "currency": row["currency"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
