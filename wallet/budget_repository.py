from typing import Any

from .config import get_db_path
from .db import database_session


class BudgetRepository:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(get_db_path())

    def get_by_month(self, month: str) -> dict[str, Any] | None:
        with database_session(self.db_path) as connection:
            row = connection.execute("SELECT * FROM budgets WHERE month = ?", (month,)).fetchone()
            return dict(row) if row is not None else None

    def set_budget(self, month: str, amount: float) -> dict[str, Any]:
        with database_session(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO budgets (month, monthly_budget, currency)
                VALUES (?, ?, 'TRY')
                ON CONFLICT(month) DO UPDATE SET
                    monthly_budget = excluded.monthly_budget,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (month, amount),
            )
            row = connection.execute("SELECT * FROM budgets WHERE month = ?", (month,)).fetchone()
            return dict(row)

    def get_by_id(self, budget_id: int) -> dict[str, Any] | None:
        with database_session(self.db_path) as connection:
            row = connection.execute("SELECT * FROM budgets WHERE id = ?", (budget_id,)).fetchone()
            return dict(row) if row is not None else None
