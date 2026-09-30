import sqlite3
from typing import Any

from .config import get_db_path


class IncomeRepository:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(get_db_path())

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def add_income(self, month: str, source_name: str, amount: float) -> dict[str, Any]:
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO income (month, source_name, amount) VALUES (?, ?, ?)",
                (month, source_name, amount),
            )
            connection.commit()

        income_id = cursor.lastrowid
        return self.get_by_id(income_id)

    def list_by_month(self, month: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, month, source_name, amount, created_at FROM income WHERE month = ? ORDER BY created_at DESC",
                (month,),
            ).fetchall()

        return [self._row_to_dict(row) for row in rows]

    def get_by_id(self, income_id: int) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, month, source_name, amount, created_at FROM income WHERE id = ?",
                (income_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_dict(row)

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "month": row["month"],
            "source_name": row["source_name"],
            "amount": row["amount"],
            "created_at": row["created_at"],
        }
