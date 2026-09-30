from typer.testing import CliRunner

from wallet.cli import app
from wallet.db import initialize_database
from wallet.dashboard_service import DashboardService
from wallet.expense_service import ExpenseService
from wallet.income_service import IncomeService
from wallet.budget_service import BudgetService


def test_dashboard_summary_calculates_monthly_financial_totals(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    BudgetService().set_budget(5000)
    IncomeService().add_income("Salary", 3500)
    IncomeService().add_income("Freelance", 1500)
    ExpenseService().add_expense(1200, "Housing")
    ExpenseService().add_expense(300, "Food")
    ExpenseService().add_expense(200, "Transport")

    summary = DashboardService().get_monthly_summary()

    assert summary["budget"] == 5000
    assert summary["total_income"] == 5000
    assert summary["total_expenses"] == 1700
    assert summary["required_expenses"] == 1200
    assert summary["discretionary_expenses"] == 500
    assert summary["remaining_budget"] == 3300
    assert summary["expense_count"] == 3
    assert summary["budget_usage_percentage"] == 34.0
    assert len(summary["category_totals"]) >= 3
    assert len(summary["recent_expenses"]) == 3


def test_dashboard_summary_handles_empty_month_without_budget(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    summary = DashboardService().get_monthly_summary()

    assert summary["budget"] == 0
    assert summary["total_income"] == 0
    assert summary["total_expenses"] == 0
    assert summary["required_expenses"] == 0
    assert summary["discretionary_expenses"] == 0
    assert summary["remaining_budget"] == 0
    assert summary["expense_count"] == 0
    assert summary["budget_usage_percentage"] == 0
    assert summary["category_totals"] == []
    assert summary["recent_expenses"] == []


def test_root_wallet_command_renders_dashboard_summary(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    BudgetService().set_budget(2400)
    IncomeService().add_income("Salary", 3000)
    ExpenseService().add_expense(500, "Food")

    runner = CliRunner()
    result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert "BudgetStream" in result.output
    assert "Total income" in result.output
    assert "Expense Count" in result.output
    assert "Budget Usage" in result.output
    assert "Remaining budget" in result.output


def test_dashboard_summary_tracks_overspending_usage_above_100_percent(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    BudgetService().set_budget(30000)
    ExpenseService().add_expense(20000, "Food")
    ExpenseService().add_expense(27000, "Housing")

    summary = DashboardService().get_monthly_summary()

    assert summary["budget_usage_percentage"] > 100
    assert summary["remaining_budget"] < 0
