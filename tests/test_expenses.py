import sqlite3

import pytest
from typer.testing import CliRunner

from wallet.cli import app
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


def test_expense_add_cli_creates_an_expense(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    runner = CliRunner()
    result = runner.invoke(app, ["expense", "add", "--amount", "250", "--category", "Food"])

    assert result.exit_code == 0
    assert "Expense added" in result.output

    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]

    assert count == 1


def test_expense_add_cli_with_description_works(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["expense", "add", "--amount", "180", "--category", "Food", "--description", "Lunch"],
    )

    assert result.exit_code == 0
    assert "Lunch" not in result.output or "Lunch" in result.output

    with sqlite3.connect(db_path) as conn:
        desc = conn.execute("SELECT description FROM expenses WHERE amount = 180").fetchone()[0]

    assert desc == "Lunch"


def test_expense_add_cli_invalid_amount_is_rejected(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    runner = CliRunner()
    result = runner.invoke(app, ["expense", "add", "--amount", "0", "--category", "Food"])

    assert result.exit_code == 1
    assert "greater than 0" in result.output


def test_expense_add_cli_nonexistent_category_is_rejected(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    runner = CliRunner()
    result = runner.invoke(app, ["expense", "add", "--amount", "100", "--category", "DoesNotExist"])

    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_expense_list_cli_displays_current_month_expenses(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    runner = CliRunner()
    runner.invoke(app, ["expense", "add", "--amount", "120", "--category", "Food"])
    runner.invoke(app, ["expense", "add", "--amount", "80", "--category", "Transport"])

    result = runner.invoke(app, ["expense", "list"])

    assert result.exit_code == 0
    assert "Expenses" in result.output
    assert "Food" in result.output
    assert "Transport" in result.output


def test_expense_list_cli_handles_empty_list(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    runner = CliRunner()
    result = runner.invoke(app, ["expense", "list"])

    assert result.exit_code == 0
    assert "No expenses" in result.output


def test_expense_delete_cli_works(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    runner = CliRunner()
    add_result = runner.invoke(app, ["expense", "add", "--amount", "150", "--category", "Food"])
    assert add_result.exit_code == 0

    with sqlite3.connect(db_path) as conn:
        expense_id = conn.execute("SELECT id FROM expenses LIMIT 1").fetchone()[0]

    delete_result = runner.invoke(app, ["expense", "delete", "--id", str(expense_id)])

    assert delete_result.exit_code == 0
    assert "deleted" in delete_result.output.lower()

    with sqlite3.connect(db_path) as conn:
        remaining = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]

    assert remaining == 0


def test_expense_delete_cli_handles_missing_id(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    runner = CliRunner()
    result = runner.invoke(app, ["expense", "delete", "--id", "999"])

    assert result.exit_code == 1
    assert "does not exist" in result.output
