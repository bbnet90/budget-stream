import sqlite3
from typing import Any

from .config import get_db_path
from .db import database_session


class CategoryRepository:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(get_db_path())

    def list_categories(self) -> list[dict[str, Any]]:
        with database_session(self.db_path) as connection:
            rows = connection.execute(
                "SELECT id, name, kind, is_default, created_at FROM categories ORDER BY name ASC"
            ).fetchall()

        return [self._row_to_dict(row) for row in rows]

    def get_category_by_name(self, name: str) -> dict[str, Any] | None:
        with database_session(self.db_path) as connection:
            row = connection.execute(
                "SELECT id, name, kind, is_default, created_at FROM categories WHERE name = ?",
                (name.strip(),),
            ).fetchone()

        return self._row_to_dict(row) if row else None

    def add_category(self, name: str, kind: str, is_default: bool = False) -> dict[str, Any]:
        with database_session(self.db_path) as connection:
            cursor = connection.execute(
                "INSERT INTO categories (name, kind, is_default) VALUES (?, ?, ?)",
                (name.strip(), kind, int(is_default)),
            )
            row = connection.execute(
                "SELECT id, name, kind, is_default, created_at FROM categories WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
            return self._row_to_dict(row)

    def get_category_by_id(self, category_id: int) -> dict[str, Any] | None:
        with database_session(self.db_path) as connection:
            row = connection.execute(
                "SELECT id, name, kind, is_default, created_at FROM categories WHERE id = ?",
                (category_id,),
            ).fetchone()

        return self._row_to_dict(row) if row else None

    def delete_category(self, category_id: int) -> None:
        with database_session(self.db_path) as connection:
            deleted = connection.execute("DELETE FROM categories WHERE id = ?", (category_id,))
            if not deleted.rowcount:
                raise ValueError(f"Category with id {category_id} does not exist.")

    def has_expenses(self, category_id: int) -> bool:
        with database_session(self.db_path) as connection:
            row = connection.execute(
                "SELECT 1 FROM expenses WHERE category_id = ? LIMIT 1",
                (category_id,),
            ).fetchone()

        return row is not None

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {**row, "is_default": bool(row["is_default"])}
