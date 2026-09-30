from datetime import date

from typer.testing import CliRunner

from wallet.budget_service import BudgetService
from wallet.cli import app
from wallet.dashboard_service import DashboardService
from wallet.db import initialize_database
from wallet.expense_service import ExpenseService
from wallet.income_service import IncomeService
from wallet.recurring_service import RecurringService


def test_recurring_income_can_be_created(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    recurring = RecurringService().add_recurring(
        type_="income",
        source_name="Salary",
        amount=45000,
        frequency="monthly",
        next_run_date="2026-10-01",
    )

    assert recurring["type"] == "income"
    assert recurring["source_name"] == "Salary"
    assert recurring["amount"] == 45000
    assert recurring["is_active"] == 1


def test_recurring_expense_can_be_created(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    recurring = RecurringService().add_recurring(
        type_="expense",
        category_name="Rent",
        amount=15000,
        description="Monthly rent",
        frequency="monthly",
        next_run_date="2026-10-01",
    )

    assert recurring["type"] == "expense"
    assert recurring["category_name"] == "Rent"
    assert recurring["amount"] == 15000
    assert recurring["is_active"] == 1


def test_recurring_rejects_invalid_amount(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    try:
        RecurringService().add_recurring(
            type_="income",
            source_name="Salary",
            amount=0,
            frequency="monthly",
            next_run_date="2026-10-01",
        )
        assert False
    except ValueError as exc:
        assert "greater than 0" in str(exc)


def test_recurring_rejects_invalid_category(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    try:
        RecurringService().add_recurring(
            type_="expense",
            category_name="DoesNotExist",
            amount=100,
            frequency="monthly",
            next_run_date="2026-10-01",
        )
        assert False
    except ValueError as exc:
        assert "does not exist" in str(exc)


def test_recurring_rejects_invalid_type(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    try:
        RecurringService().add_recurring(
            type_="bonus",
            source_name="Test",
            amount=100,
            frequency="monthly",
            next_run_date="2026-10-01",
        )
        assert False
    except ValueError as exc:
        assert "income or expense" in str(exc)


def test_recurring_list_returns_sorted_entries(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    RecurringService().add_recurring(
        type_="income",
        source_name="Salary",
        amount=45000,
        frequency="monthly",
        next_run_date="2026-10-01",
    )
    RecurringService().add_recurring(
        type_="expense",
        category_name="Rent",
        amount=15000,
        frequency="monthly",
        next_run_date="2026-09-01",
    )

    recurring = RecurringService().list_recurring()
    assert [item["type"] for item in recurring] == ["expense", "income"]


def test_recurring_can_be_disabled_and_enabled(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    recurring = RecurringService().add_recurring(
        type_="income",
        source_name="Salary",
        amount=45000,
        frequency="monthly",
        next_run_date="2026-10-01",
    )

    RecurringService().disable_recurring(recurring["id"])
    assert RecurringService().get_recurring_by_id(recurring["id"])["is_active"] == 0

    RecurringService().enable_recurring(recurring["id"])
    assert RecurringService().get_recurring_by_id(recurring["id"])["is_active"] == 1


def test_recurring_can_be_deleted_without_harming_history(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    recurring = RecurringService().add_recurring(
        type_="income",
        source_name="Salary",
        amount=45000,
        frequency="monthly",
        next_run_date="2026-10-01",
    )
    IncomeService().add_income("Salary", 1000)

    RecurringService().delete_recurring(recurring["id"])
    assert RecurringService().get_recurring_by_id(recurring["id"]) is None
    assert IncomeService().list_current_month_income()[0]["amount"] == 1000


def test_recurring_apply_creates_income_record(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    RecurringService().add_recurring(
        type_="income",
        source_name="Salary",
        amount=45000,
        frequency="monthly",
        next_run_date="2026-09-01",
    )

    applied = RecurringService().apply_due_recurring(today=date(2026, 9, 30))

    assert applied[0]["type"] == "income"
    assert len(IncomeService().list_current_month_income()) == 1
    assert IncomeService().list_current_month_income()[0]["amount"] == 45000
    assert RecurringService().list_recurring()[0]["next_run_date"] == "2026-10-01"


def test_recurring_apply_creates_expense_record(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    RecurringService().add_recurring(
        type_="expense",
        category_name="Rent",
        amount=15000,
        description="Monthly rent",
        frequency="monthly",
        next_run_date="2026-09-01",
    )

    RecurringService().apply_due_recurring(today=date(2026, 9, 30))

    expenses = ExpenseService().list_current_month_expenses()
    assert len(expenses) == 1
    assert expenses[0]["amount"] == 15000
    assert expenses[0]["category_name"] == "Rent"


def test_recurring_inactive_and_future_are_ignored(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    recurring = RecurringService().add_recurring(
        type_="income",
        source_name="Salary",
        amount=45000,
        frequency="monthly",
        next_run_date="2026-09-01",
    )
    RecurringService().disable_recurring(recurring["id"])
    RecurringService().apply_due_recurring(today=date(2026, 9, 30))
    assert IncomeService().list_current_month_income() == []

    future = RecurringService().add_recurring(
        type_="income",
        source_name="Bonus",
        amount=1000,
        frequency="monthly",
        next_run_date="2026-12-01",
    )
    RecurringService().apply_due_recurring(today=date(2026, 9, 30))
    assert RecurringService().get_recurring_by_id(future["id"])["next_run_date"] == "2026-12-01"


def test_recurring_apply_is_idempotent(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    RecurringService().add_recurring(
        type_="income",
        source_name="Salary",
        amount=45000,
        frequency="monthly",
        next_run_date="2026-09-01",
    )

    RecurringService().apply_due_recurring(today=date(2026, 9, 30))
    first = len(IncomeService().list_current_month_income())
    RecurringService().apply_due_recurring(today=date(2026, 9, 30))
    second = len(IncomeService().list_current_month_income())

    assert first == 1
    assert second == 1


def test_recurring_monthly_catch_up_and_month_end_rollover(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    RecurringService().add_recurring(
        type_="income",
        source_name="Salary",
        amount=2000,
        frequency="monthly",
        next_run_date="2026-07-31",
    )

    applied = RecurringService().apply_due_recurring(today=date(2026, 9, 30))

    assert len(applied) == 3
    assert RecurringService().list_recurring()[0]["next_run_date"] == "2026-10-30"

    import sqlite3

    with sqlite3.connect(db_path) as conn:
        total_incomes = conn.execute("SELECT COUNT(*) FROM income").fetchone()[0]

    assert total_incomes == 3


def test_recurring_cli_commands_work(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    runner = CliRunner()
    add_result = runner.invoke(
        app,
        [
            "recurring",
            "add",
            "--type",
            "income",
            "--source",
            "Salary",
            "--amount",
            "45000",
            "--frequency",
            "monthly",
            "--next-run",
            "2026-10-01",
        ],
    )
    assert add_result.exit_code == 0
    assert "Salary" in add_result.output

    list_result = runner.invoke(app, ["recurring", "list"])
    assert list_result.exit_code == 0
    assert "Active" in list_result.output

    apply_result = runner.invoke(app, ["recurring", "apply"])
    assert apply_result.exit_code == 0
    assert "applied" in apply_result.output.lower()
