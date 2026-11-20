from __future__ import annotations

import sqlite3

from .category_repository import CategoryRepository

VALID_KINDS = {"required", "discretionary"}


class CategoryService:
    def __init__(self, repository: CategoryRepository | None = None):
        self.repository = repository or CategoryRepository()

    @staticmethod
    def normalize_name(name: str) -> str:
        cleaned = (name or "").strip()
        if not cleaned:
            raise ValueError("Category name cannot be empty.")
        return cleaned

    @staticmethod
    def normalize_kind(kind: str) -> str:
        cleaned = (kind or "").strip().lower()
        if cleaned not in VALID_KINDS:
            raise ValueError("Category kind must be required or discretionary.")
        return cleaned

    def list_categories(self) -> list[dict]:
        return self.repository.list_categories()

    def get_category(self, name: str) -> dict | None:
        cleaned = self.normalize_name(name)
        return self.repository.get_category_by_name(cleaned)

    def add_category(self, name: str, kind: str) -> dict:
        cleaned_name = self.normalize_name(name)
        cleaned_kind = self.normalize_kind(kind)

        try:
            return self.repository.add_category(cleaned_name, cleaned_kind)
        except sqlite3.IntegrityError as exc:
            if exc.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_UNIQUE:
                raise ValueError(f'Category "{cleaned_name}" already exists.') from exc
            raise

    def delete_category(self, name: str) -> bool:
        cleaned_name = self.normalize_name(name)
        category = self.repository.get_category_by_name(cleaned_name)

        if category is None:
            raise ValueError(f'Category "{cleaned_name}" does not exist.')

        if category["is_default"]:
            raise ValueError(f'default category "{cleaned_name}" cannot be deleted.')

        try:
            self.repository.delete_category(category["id"])
        except sqlite3.IntegrityError as exc:
            if exc.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_FOREIGNKEY:
                raise ValueError(
                    f'Category "{cleaned_name}" cannot be deleted while an expense or recurring transaction uses it.'
                ) from exc
            raise
        return True
