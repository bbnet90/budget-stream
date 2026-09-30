import sqlite3
from typing import Any

from wallet.db import get_connection


class RecurringRepository:
    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        if row is None:
            return None
        return {
            "id": row["id"],
            "type": row["type"],
            "source_name": row["source_name"],
            "category_id": row["category_id"],
            "category_name": row["category_name"],
            "amount": row["amount"],
            "description": row["description"],
            "frequency": row["frequency"],
            "next_run_date": row["next_run_date"],
            "is_active": row["is_active"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

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
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO recurring_transactions (
                    type,
                    source_name,
                    category_id,
                    amount,
                    description,
                    frequency,
                    next_run_date,
                    is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    type_,
                    source_name,
                    category_id,
                    amount,
                    description,
                    frequency,
                    next_run_date,
                    is_active,
                ),
            )
            conn.commit()
            recurring_id = cursor.lastrowid
            return self.get_by_id(recurring_id)

    def get_by_id(self, recurring_id: int) -> dict[str, Any] | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT rt.*, c.name AS category_name
                FROM recurring_transactions rt
                LEFT JOIN categories c ON c.id = rt.category_id
                WHERE rt.id = ?
                """,
                (recurring_id,),
            ).fetchone()
            return self._row_to_dict(row)

    def list_all(self) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT rt.*, c.name AS category_name
                FROM recurring_transactions rt
                LEFT JOIN categories c ON c.id = rt.category_id
                ORDER BY rt.next_run_date ASC, rt.id ASC
                """
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_active_due(self, today_iso: str) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT rt.*, c.name AS category_name
                FROM recurring_transactions rt
                LEFT JOIN categories c ON c.id = rt.category_id
                WHERE rt.is_active = 1 AND rt.next_run_date <= ?
                ORDER BY rt.next_run_date ASC, rt.id ASC
                """,
                (today_iso,),
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def update_status(self, recurring_id: int, is_active: int) -> dict[str, Any] | None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE recurring_transactions SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (is_active, recurring_id),
            )
            conn.commit()
        return self.get_by_id(recurring_id)

    def update_next_run_date(self, recurring_id: int, next_run_date: str) -> dict[str, Any] | None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE recurring_transactions SET next_run_date = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (next_run_date, recurring_id),
            )
            conn.commit()
        return self.get_by_id(recurring_id)

    def delete_by_id(self, recurring_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM recurring_transactions WHERE id = ?", (recurring_id,))
            conn.commit()
