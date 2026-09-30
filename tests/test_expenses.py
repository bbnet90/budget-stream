import sqlite3

import pytest

from wallet.db import initialize_database
from wallet.expense_service import ExpenseService
from wallet.services import current_month_key


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()
    return db_path


def test_expense_can_be_created(isolated_db):
    service = ExpenseService()
    expense = service.add_expense(250, "Food")

    assert expense["amount"] == 250
    assert expense["category_name"] == "Food"


def test_expense_amount_is_stored_correctly(isolated_db):
    service = ExpenseService()
    expense = service.add_expense(180, "Food")

    assert expense["amount"] == 180


def test_category_relationship_is_stored_correctly(isolated_db):
    service = ExpenseService()
    expense = service.add_expense(50, "Housing")

    assert expense["category_name"] == "Housing"
    assert expense["category_id"] == 2 or expense["category_id"] > 0


def test_existing_category_is_required(isolated_db):
    service = ExpenseService()

    with pytest.raises(ValueError, match="Category"):
        service.add_expense(100, "DoesNotExist")


def test_non_existent_category_is_rejected(isolated_db):
    service = ExpenseService()

    with pytest.raises(ValueError, match="does not exist"):
        service.add_expense(100, "DoesNotExist")


def test_zero_amount_is_rejected(isolated_db):
    service = ExpenseService()

    with pytest.raises(ValueError, match="greater than 0"):
        service.add_expense(0, "Food")


def test_negative_amount_is_rejected(isolated_db):
    service = ExpenseService()

    with pytest.raises(ValueError, match="greater than 0"):
        service.add_expense(-100, "Food")


def test_optional_description_is_stored(isolated_db):
    service = ExpenseService()
    expense = service.add_expense(120, "Food", description="Lunch")

    assert expense["description"] == "Lunch"


def test_expense_date_defaults_correctly(isolated_db):
    service = ExpenseService()
    expense = service.add_expense(90, "Food")

    assert expense["expense_date"].startswith(current_month_key()[:7])


def test_multiple_expenses_can_exist(isolated_db):
    service = ExpenseService()
    service.add_expense(120, "Food")
    service.add_expense(50, "Transport")

    expenses = service.list_current_month_expenses()
    assert len(expenses) == 2


def test_current_month_expense_listing_works(isolated_db):
    service = ExpenseService()
    service.add_expense(120, "Food")
    service.add_expense(80, "Transport")

    expenses = service.list_current_month_expenses()
    assert len(expenses) == 2
    categories = {item["category_name"] for item in expenses}
    assert categories == {"Food", "Transport"}


def test_empty_expense_listing_is_handled_cleanly(isolated_db):
    service = ExpenseService()

    assert service.list_current_month_expenses() == []


def test_existing_expense_can_be_deleted(isolated_db):
    service = ExpenseService()
    expense = service.add_expense(100, "Food")

    result = service.delete_expense(expense["id"])

    assert result is True
    assert service.list_current_month_expenses() == []


def test_deleting_a_non_existent_expense_is_handled_cleanly(isolated_db):
    service = ExpenseService()

    with pytest.raises(ValueError, match="does not exist"):
        service.delete_expense(999)


def test_deleting_an_expense_does_not_delete_its_category(isolated_db):
    service = ExpenseService()
    expense = service.add_expense(100, "Food")

    service.delete_expense(expense["id"])

    with sqlite3.connect(isolated_db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM categories WHERE name = 'Food'").fetchone()[0]

    assert count == 1


def test_category_required_kind_is_used_for_expense_is_required(isolated_db):
    service = ExpenseService()
    expense = service.add_expense(100, "Housing")

    assert expense["is_required"] == 1
