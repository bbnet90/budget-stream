import sqlite3
from typing import Any

from .config import get_db_path
from .db import database_session


def insert_income(connection: sqlite3.Connection, month: str, source_name: str, amount: float) -> dict[str, Any]:
    cursor = connection.execute(
        "INSERT INTO income (month, source_name, amount) VALUES (?, ?, ?)",
        (month, source_name, amount),
    )
    row = connection.execute("SELECT * FROM income WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


class IncomeRepository:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(get_db_path())

    def add_income(self, month: str, source_name: str, amount: float) -> dict[str, Any]:
        with database_session(self.db_path) as connection:
            return insert_income(connection, month, source_name, amount)

    def list_by_month(self, month: str) -> list[dict[str, Any]]:
        with database_session(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM income WHERE month = ? ORDER BY created_at DESC, id DESC",
                (month,),
            )
            return [dict(row) for row in rows]

    def get_by_id(self, income_id: int) -> dict[str, Any] | None:
        with database_session(self.db_path) as connection:
            row = connection.execute("SELECT * FROM income WHERE id = ?", (income_id,)).fetchone()
            return dict(row) if row is not None else None
