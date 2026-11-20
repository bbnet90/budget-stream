import sqlite3
from contextlib import nullcontext
from typing import Any

from wallet.db import database_session
from wallet.expense_repository import insert_expense
from wallet.income_repository import insert_income


_SELECT_RECURRING = """
    SELECT rt.*, c.name AS category_name
    FROM recurring_transactions rt
    LEFT JOIN categories c ON c.id = rt.category_id
"""
_ORDER = " ORDER BY rt.next_run_date, rt.id"


class RecurringRepository:
    @staticmethod
    def _get_by_id(conn: sqlite3.Connection, recurring_id: int | None) -> dict[str, Any] | None:
        row = conn.execute(_SELECT_RECURRING + " WHERE rt.id = ?", (recurring_id,)).fetchone()
        return dict(row) if row is not None else None

    def add_recurring(
        self,
        type_: str,
        source_name: str | None,
        category_id: int | None,
        amount: float,
        description: str | None,
        frequency: str,
        next_run_date: str,
        is_active: int = 1,
    ) -> dict[str, Any]:
        with database_session() as conn:
            cursor = conn.execute(
                """
                INSERT INTO recurring_transactions (
                    type, source_name, category_id, amount, description, frequency, next_run_date, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (type_, source_name, category_id, amount, description, frequency, next_run_date, is_active),
            )
            created = self._get_by_id(conn, cursor.lastrowid)
            if created is None:
                raise RuntimeError("Recurring transaction could not be loaded.")
            return created

    def get_by_id(self, recurring_id: int) -> dict[str, Any] | None:
        with database_session() as conn:
            return self._get_by_id(conn, recurring_id)

    def list_all(self) -> list[dict[str, Any]]:
        with database_session() as conn:
            return [dict(row) for row in conn.execute(_SELECT_RECURRING + _ORDER)]

    def get_active_due(
        self, today_iso: str, connection: sqlite3.Connection | None = None
    ) -> list[dict[str, Any]]:
        with (database_session() if connection is None else nullcontext(connection)) as conn:
            rows = conn.execute(
                _SELECT_RECURRING + " WHERE rt.is_active = 1 AND rt.next_run_date <= ?" + _ORDER,
                (today_iso,),
            )
            return [dict(row) for row in rows]

    def apply_occurrences(
        self,
        recurring: dict[str, Any],
        due_dates: list[str],
        next_run_date: str,
        connection: sqlite3.Connection | None = None,
    ) -> list[dict[str, Any]]:
        with (database_session() if connection is None else nullcontext(connection)) as conn:
            advanced = conn.execute(
                """
                UPDATE recurring_transactions
                SET next_run_date = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND next_run_date = ? AND is_active = 1
                """,
                (next_run_date, recurring["id"], recurring["next_run_date"]),
            )
            if advanced.rowcount == 0:
                return []
            if recurring["type"] == "income":
                return [
                    insert_income(conn, due_date[:7], recurring["source_name"], recurring["amount"])
                    for due_date in due_dates
                ]

            category = conn.execute(
                "SELECT kind FROM categories WHERE id = ?", (recurring["category_id"],)
            ).fetchone()
            if category is None:
                raise ValueError(f"Recurring expense #{recurring['id']} refers to a missing category.")
            return [
                insert_expense(
                    conn,
                    recurring["category_id"],
                    recurring["amount"],
                    recurring["description"] or "Recurring expense",
                    due_date,
                    int(category["kind"] == "required"),
                )
                for due_date in due_dates
            ]

    def update_status(self, recurring_id: int, is_active: int) -> dict[str, Any] | None:
        with database_session() as conn:
            conn.execute(
                "UPDATE recurring_transactions SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (is_active, recurring_id),
            )
            return self._get_by_id(conn, recurring_id)

    def delete_by_id(self, recurring_id: int) -> bool:
        with database_session() as conn:
            deleted = conn.execute("DELETE FROM recurring_transactions WHERE id = ?", (recurring_id,))
            return deleted.rowcount == 1
