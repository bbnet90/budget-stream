from contextlib import contextmanager
from copy import copy
from decimal import Decimal
from typing import Any

from .config import get_db_path


from .db import database_session


class DecimalSum:
    def __init__(self):
        self.total = Decimal(0)

    def step(self, amount):
        self.total += Decimal(str(amount))

    def finalize(self):
        return float(self.total)


class DashboardRepository:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(get_db_path())

    _connection = None

    @contextmanager
    def _connect(self):
        if self._connection is not None:
            yield self._connection
        else:
            with database_session(self.db_path) as connection:
                connection.create_aggregate("decimal_sum", 1, DecimalSum)
                yield connection

    @contextmanager
    def snapshot(self):
        with self._connect() as connection:
            connection.execute("BEGIN")
            reader = copy(self)
            reader._connection = connection
            yield reader

    def get_total_income_for_month(self, month: str) -> float:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(decimal_sum(amount), 0) FROM income WHERE month = ?",
                (month,),
            ).fetchone()

        return float(row[0] or 0)

    def get_budget_for_month(self, month: str) -> float:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT monthly_budget FROM budgets WHERE month = ?",
                (month,),
            ).fetchone()

        if row is None:
            return 0.0

        return float(row[0] or 0)

    def has_budget_for_month(self, month: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM budgets WHERE month = ? LIMIT 1",
                (month,),
            ).fetchone()

        return row is not None

    def get_expense_totals_for_month(self, month: str) -> dict[str, float]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    COALESCE(decimal_sum(amount), 0) AS total_expenses,
                    COALESCE(decimal_sum(CASE WHEN is_required = 1 THEN amount ELSE 0 END), 0) AS required_expenses,
                    COALESCE(decimal_sum(CASE WHEN is_required = 0 THEN amount ELSE 0 END), 0) AS discretionary_expenses
                FROM expenses
                WHERE substr(expense_date, 1, 7) = ?
                """,
                (month,),
            ).fetchone()

        return {
            "total_expenses": float(row["total_expenses"] or 0),
            "required_expenses": float(row["required_expenses"] or 0),
            "discretionary_expenses": float(row["discretionary_expenses"] or 0),
        }

    def get_expense_count_for_month(self, month: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM expenses WHERE substr(expense_date, 1, 7) = ?",
                (month,),
            ).fetchone()

        return int(row[0] or 0)

    def get_category_totals_for_month(self, month: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT c.name AS category, decimal_sum(e.amount) AS total
                FROM expenses e JOIN categories c ON c.id = e.category_id
                WHERE substr(e.expense_date, 1, 7) = ?
                GROUP BY c.id, c.name
                ORDER BY total DESC, c.name ASC
                """,
                (month,),
            ).fetchall()

        return [dict(row) for row in rows]

    def get_recent_expenses_for_month(self, month: str, limit: int = 5) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT e.id, e.expense_date, c.name AS category_name, e.amount, e.description, e.is_required
                FROM expenses e
                JOIN categories c ON c.id = e.category_id
                WHERE substr(e.expense_date, 1, 7) = ?
                ORDER BY e.expense_date DESC, e.id DESC
                LIMIT ?
                """,
                (month, limit),
            ).fetchall()

        return [
            {
                "id": row["id"],
                "date": row["expense_date"],
                "category": row["category_name"],
                "amount": float(row["amount"] or 0),
                "description": row["description"],
                "is_required": bool(row["is_required"]),
            }
            for row in rows
        ]
