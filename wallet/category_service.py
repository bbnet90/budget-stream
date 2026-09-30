from __future__ import annotations

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

        existing = self.repository.get_category_by_name(cleaned_name)
        if existing is not None:
            raise ValueError(f'Category "{cleaned_name}" already exists.')

        return self.repository.add_category(cleaned_name, cleaned_kind, is_default=False)

    def delete_category(self, name: str) -> bool:
        cleaned_name = self.normalize_name(name)
        category = self.repository.get_category_by_name(cleaned_name)

        if category is None:
            raise ValueError(f'Category "{cleaned_name}" does not exist.')

        if category["is_default"]:
            raise ValueError(f'default category "{cleaned_name}" cannot be deleted.')

        if self.repository.has_expenses(category["id"]):
            raise ValueError(
                f'Category "{cleaned_name}" cannot be deleted because it is referenced by one or more expenses.'
            )

        self.repository.delete_category(category["id"])
        return True
