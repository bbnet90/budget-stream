import sqlite3

import pytest

from wallet.category_service import CategoryService
from wallet.db import initialize_database


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()
    return db_path


def test_default_categories_are_created(isolated_db):
    with sqlite3.connect(isolated_db) as conn:
        names = conn.execute(
            "SELECT name FROM categories ORDER BY name"
        ).fetchall()

    category_names = {row[0] for row in names}
    assert {"Food", "Housing", "Utilities", "Transport", "Health", "Entertainment", "Shopping", "Savings", "Other"}.issubset(category_names)


def test_database_initialization_does_not_duplicate_defaults(isolated_db):
    initialize_database()

    with sqlite3.connect(isolated_db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM categories WHERE name = 'Food'").fetchone()[0]

    assert count == 1


def test_custom_category_can_be_added(isolated_db):
    service = CategoryService()
    category = service.add_category("Travel", "discretionary")

    assert category["name"] == "Travel"
    assert category["kind"] == "discretionary"
    assert category["is_default"] is False


def test_duplicate_category_names_are_rejected(isolated_db):
    service = CategoryService()
    service.add_category("Travel", "discretionary")

    with pytest.raises(ValueError, match="already exists"):
        service.add_category("Travel", "required")


def test_invalid_category_kinds_are_rejected(isolated_db):
    service = CategoryService()

    with pytest.raises(ValueError, match="required or discretionary"):
        service.add_category("Travel", "invalid")


def test_category_without_expenses_can_be_deleted(isolated_db):
    service = CategoryService()
    service.add_category("Travel", "discretionary")

    deleted = service.delete_category("Travel")

    assert deleted is True
    assert service.get_category("Travel") is None


def test_category_referenced_by_expense_cannot_be_deleted(isolated_db):
    service = CategoryService()
    category = service.add_category("Travel", "discretionary")

    with sqlite3.connect(isolated_db) as conn:
        conn.execute(
            "INSERT INTO expenses (category_id, amount, description, expense_date, is_required) VALUES (?, 100, 'Train ticket', '2026-09-05', 0)",
            (category["id"],),
        )
        conn.commit()

    with pytest.raises(ValueError, match="cannot be deleted"):
        service.delete_category("Travel")


def test_default_categories_cannot_be_deleted(isolated_db):
    service = CategoryService()

    with pytest.raises(ValueError, match="default category"):
        service.delete_category("Food")
