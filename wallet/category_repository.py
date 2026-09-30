import sqlite3
from typing import Any

from .config import get_db_path


class CategoryRepository:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(get_db_path())

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def list_categories(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, name, kind, is_default, created_at FROM categories ORDER BY name ASC"
            ).fetchall()

        return [self._row_to_dict(row) for row in rows]

    def get_category_by_name(self, name: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, name, kind, is_default, created_at FROM categories WHERE name = ?",
                (name.strip(),),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_dict(row)

    def add_category(self, name: str, kind: str, is_default: bool = False) -> dict[str, Any]:
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO categories (name, kind, is_default) VALUES (?, ?, ?)",
                (name.strip(), kind, int(is_default)),
            )
            connection.commit()

        category_id = cursor.lastrowid
        return self.get_category_by_id(category_id)

    def get_category_by_id(self, category_id: int) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, name, kind, is_default, created_at FROM categories WHERE id = ?",
                (category_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_dict(row)

    def delete_category(self, category_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM categories WHERE id = ?", (category_id,))
            connection.commit()

    def has_expenses(self, category_id: int) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM expenses WHERE category_id = ? LIMIT 1",
                (category_id,),
            ).fetchone()

        return row is not None

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "kind": row["kind"],
            "is_default": bool(row["is_default"]),
            "created_at": row["created_at"],
        }
