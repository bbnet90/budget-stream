import sqlite3
from typing import Any

from .config import get_db_path
from .db import database_session


EXPENSE_SELECT = """
    SELECT e.*, c.name AS category_name
    FROM expenses e JOIN categories c ON c.id = e.category_id
"""


def insert_expense(
    connection: sqlite3.Connection,
    category_id: int,
    amount: float,
    description: str | None,
    expense_date: str,
    is_required: int,
) -> dict[str, Any]:
    cursor = connection.execute(
        """
        INSERT INTO expenses (category_id, amount, description, expense_date, is_required)
        VALUES (?, ?, ?, ?, ?)
        """,
        (category_id, amount, description, expense_date, is_required),
    )
    row = connection.execute(EXPENSE_SELECT + " WHERE e.id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


class ExpenseRepository:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(get_db_path())

    def add_expense(
        self,
        category_id: int,
        amount: float,
        description: str | None,
        expense_date: str,
        is_required: int,
    ) -> dict[str, Any]:
        with database_session(self.db_path) as connection:
            return insert_expense(connection, category_id, amount, description, expense_date, is_required)

    def get_by_id(self, expense_id: int) -> dict[str, Any] | None:
        with database_session(self.db_path) as connection:
            row = connection.execute(EXPENSE_SELECT + " WHERE e.id = ?", (expense_id,)).fetchone()
            return dict(row) if row is not None else None

    def list_by_month(self, month: str) -> list[dict[str, Any]]:
        with database_session(self.db_path) as connection:
            rows = connection.execute(
                EXPENSE_SELECT + " WHERE substr(e.expense_date, 1, 7) = ? ORDER BY e.expense_date DESC, e.id DESC",
                (month,),
            )
            return [dict(row) for row in rows]

    def delete_by_id(self, expense_id: int) -> bool:
        with database_session(self.db_path) as connection:
            return connection.execute("DELETE FROM expenses WHERE id = ?", (expense_id,)).rowcount == 1
