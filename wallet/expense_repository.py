import sqlite3
from typing import Any

from .config import get_db_path


class ExpenseRepository:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(get_db_path())

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def add_expense(
        self,
        category_id: int,
        amount: float,
        description: str | None,
        expense_date: str,
        is_required: int,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO expenses (category_id, amount, description, expense_date, is_required)
                VALUES (?, ?, ?, ?, ?)
                """,
                (category_id, amount, description, expense_date, is_required),
            )
            connection.commit()

        expense_id = cursor.lastrowid
        return self.get_by_id(expense_id)

    def get_by_id(self, expense_id: int) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT e.id, e.category_id, c.name AS category_name, e.amount, e.description,
                       e.expense_date, e.is_required, e.created_at, e.updated_at
                FROM expenses e
                JOIN categories c ON c.id = e.category_id
                WHERE e.id = ?
                """,
                (expense_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_dict(row)

    def list_by_month(self, month: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT e.id, e.category_id, c.name AS category_name, e.amount, e.description,
                       e.expense_date, e.is_required, e.created_at, e.updated_at
                FROM expenses e
                JOIN categories c ON c.id = e.category_id
                WHERE substr(e.expense_date, 1, 7) = ?
                ORDER BY e.expense_date DESC, e.id DESC
                """,
                (month,),
            ).fetchall()

        return [self._row_to_dict(row) for row in rows]

    def delete_by_id(self, expense_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
            connection.commit()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "category_id": row["category_id"],
            "category_name": row["category_name"],
            "amount": row["amount"],
            "description": row["description"],
            "expense_date": row["expense_date"],
            "is_required": row["is_required"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
