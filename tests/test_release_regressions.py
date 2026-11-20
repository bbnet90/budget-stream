import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from typer.testing import CliRunner

from wallet.budget_service import BudgetService
from wallet.category_service import CategoryService
from wallet.cli import app
from wallet.dashboard_service import DashboardService
from wallet.db import database_session, initialize_database
from wallet.expense_service import ExpenseService
from wallet.income_service import IncomeService
from wallet.recurring_service import RecurringService
from wallet.report_service import ReportService


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(path))
    initialize_database()
    return path


def test_failed_catch_up_rolls_back_every_definition_and_retries(ledger):
    service = RecurringService()
    service.add_recurring("income", 12, next_run_date="2024-01-31", source_name="Test")
    service.add_recurring("expense", 4, next_run_date="2024-01-31", category_name="Housing")
    with database_session() as db:
        db.execute("""CREATE TRIGGER fail_second BEFORE INSERT ON expenses
                      WHEN NEW.expense_date = '2024-02-29'
                      BEGIN SELECT RAISE(ABORT, 'test failure'); END""")
    with pytest.raises(sqlite3.IntegrityError, match="test failure"):
        service.apply_due_recurring(date(2024, 2, 29))
    with database_session() as db:
        assert db.execute("SELECT COUNT(*) FROM income").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM expenses").fetchone()[0] == 0
        assert [r[0] for r in db.execute("SELECT next_run_date FROM recurring_transactions")] == ["2024-01-31"] * 2
        db.execute("DROP TRIGGER fail_second")
    assert len(service.apply_due_recurring(date(2024, 2, 29))) == 4
    assert service.apply_due_recurring(date(2024, 2, 29)) == []


def test_concurrent_catch_up_posts_once(ledger):
    service = RecurringService()
    service.add_recurring("expense", 4, next_run_date="2024-01-31", category_name="Housing")
    barrier = Barrier(4)

    def apply(_):
        barrier.wait(timeout=10)
        return len(RecurringService().apply_due_recurring(date(2024, 3, 31)))

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sorted(pool.map(apply, range(4))) == [0, 0, 0, 3]
    with database_session() as db:
        assert [r[0] for r in db.execute("SELECT expense_date FROM expenses ORDER BY id")] == [
            "2024-01-31", "2024-02-29", "2024-03-29"
        ]


def test_category_used_by_disabled_schedule_is_protected(ledger):
    categories = CategoryService()
    categories.add_category("Trip", "discretionary")
    service = RecurringService()
    item = service.add_recurring("expense", 3, next_run_date=date.today(), category_name="Trip")
    service.disable_recurring(item["id"])
    with pytest.raises(ValueError, match="cannot be deleted"):
        categories.delete_category("Trip")
    assert service.apply_due_recurring() == []


def test_balanced_fractional_expenses(ledger):
    BudgetService().set_budget(0.30)
    IncomeService().add_income("Test", 0.30)
    for amount in (0.10, 0.20):
        ExpenseService().add_expense(amount, "Food")
    summary = DashboardService().get_monthly_summary()
    assert summary["total_expenses"] == 0.30
    assert summary["daily_available"] == 0
    assert ReportService().get_current_report()["income_vs_expense"]["net_cash_flow"] == 0


@pytest.mark.parametrize("amount", [float("inf"), float("nan")])
def test_nonfinite_money_rejected(ledger, amount):
    for action in (lambda: BudgetService().set_budget(amount),
                   lambda: IncomeService().add_income("Test", amount),
                   lambda: ExpenseService().add_expense(amount, "Food"),
                   lambda: RecurringService().add_recurring("income", amount, source_name="Test", next_run_date=date.today())):
        with pytest.raises(ValueError, match="finite"):
            action()


def test_labels_and_cents_display_literally(ledger):
    IncomeService().add_income("Earnings [net]", 0.49)
    result = CliRunner().invoke(app, ["income", "list"])
    assert result.exit_code == 0
    assert "Earnings [net]" in result.output and "0.49" in result.output
