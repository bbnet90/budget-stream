import sqlite3
from typing import Any

from .config import get_db_path


class DashboardRepository:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(get_db_path())

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def get_total_income_for_month(self, month: str) -> float:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM income WHERE month = ?",
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
                    COALESCE(SUM(amount), 0) AS total_expenses,
                    COALESCE(SUM(CASE WHEN is_required = 1 THEN amount ELSE 0 END), 0) AS required_expenses,
                    COALESCE(SUM(CASE WHEN is_required = 0 THEN amount ELSE 0 END), 0) AS discretionary_expenses
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
                SELECT c.name AS category_name,
                       COALESCE(SUM(CASE WHEN substr(e.expense_date, 1, 7) = ? THEN e.amount ELSE 0 END), 0) AS total_amount
                FROM categories c
                LEFT JOIN expenses e ON e.category_id = c.id
                GROUP BY c.id, c.name
                HAVING total_amount > 0
                ORDER BY total_amount DESC, c.name ASC
                """,
                (month,),
            ).fetchall()

        items: list[dict[str, Any]] = []
        for row in rows:
            amount = float(row["total_amount"] or 0)
            if amount == 0:
                continue
            items.append({
                "category": row["category_name"],
                "total": amount,
            })

        return items

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
