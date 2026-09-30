from typer.testing import CliRunner

from wallet.budget_service import BudgetService
from wallet.cli import app
from wallet.db import initialize_database
from wallet.expense_service import ExpenseService
from wallet.income_service import IncomeService
from wallet.report_service import ReportService


def test_report_service_returns_expected_financial_summary(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    BudgetService().set_budget(30000)
    IncomeService().add_income("Salary", 45000)
    ExpenseService().add_expense(5000, "Housing")
    ExpenseService().add_expense(1500, "Food")
    ExpenseService().add_expense(500, "Food")

    report = ReportService().get_current_report()

    assert report["income_vs_expense"]["total_income"] == 45000
    assert report["income_vs_expense"]["total_expenses"] == 7000
    assert report["income_vs_expense"]["net_cash_flow"] == 38000
    assert report["income_vs_expense"]["expense_to_income_percentage"] == 15.56

    assert report["expense_breakdown"]["required_expenses"] == 5000
    assert report["expense_breakdown"]["discretionary_expenses"] == 2000
    assert report["expense_breakdown"]["required_share_percentage"] == 71.43
    assert report["expense_breakdown"]["discretionary_share_percentage"] == 28.57

    assert report["budget_comparison"]["monthly_budget"] == 30000
    assert report["budget_comparison"]["remaining_budget"] == 23000
    assert report["budget_comparison"]["budget_usage_percentage"] == 23.33

    assert report["category_spending"][0]["category"] == "Housing"
    assert report["category_spending"][0]["amount"] == 5000
    assert report["category_spending"][0]["percentage_of_total_expenses"] == 71.43
    assert report["category_spending"][1]["category"] == "Food"
    assert report["category_spending"][1]["amount"] == 2000
    assert report["category_spending"][1]["percentage_of_total_expenses"] == 28.57


def test_report_service_handles_zero_expenses(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    BudgetService().set_budget(30000)
    IncomeService().add_income("Salary", 45000)

    report = ReportService().get_current_report()

    assert report["income_vs_expense"]["total_expenses"] == 0
    assert report["income_vs_expense"]["net_cash_flow"] == 45000
    assert report["income_vs_expense"]["expense_to_income_percentage"] == 0.0
    assert report["expense_breakdown"]["required_share_percentage"] == 0.0
    assert report["expense_breakdown"]["discretionary_share_percentage"] == 0.0
    assert report["budget_comparison"]["remaining_budget"] == 30000
    assert report["budget_comparison"]["budget_usage_percentage"] == 0.0
    assert report["category_spending"] == []


def test_report_service_handles_zero_income(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    BudgetService().set_budget(30000)
    ExpenseService().add_expense(5000, "Housing")

    report = ReportService().get_current_report()

    assert report["income_vs_expense"]["total_income"] == 0
    assert report["income_vs_expense"]["expense_to_income_percentage"] == 0.0
    assert report["income_vs_expense"]["net_cash_flow"] == -5000


def test_report_service_handles_overspending(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    BudgetService().set_budget(30000)
    IncomeService().add_income("Salary", 45000)
    ExpenseService().add_expense(50000, "Housing")

    report = ReportService().get_current_report()

    assert report["income_vs_expense"]["net_cash_flow"] == -5000
    assert report["budget_comparison"]["remaining_budget"] == -20000
    assert report["budget_comparison"]["budget_usage_percentage"] == 166.67


def test_report_service_deterministic_category_ordering(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    BudgetService().set_budget(20000)
    ExpenseService().add_expense(1000, "Food")
    ExpenseService().add_expense(1000, "Housing")
    ExpenseService().add_expense(2000, "Transport")

    report = ReportService().get_current_report()

    ordered_names = [item["category"] for item in report["category_spending"]]
    assert ordered_names == ["Transport", "Food", "Housing"]


def test_report_service_handles_empty_database(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    report = ReportService().get_current_report()

    assert report["income_vs_expense"]["total_income"] == 0
    assert report["income_vs_expense"]["total_expenses"] == 0
    assert report["expense_breakdown"]["required_expenses"] == 0
    assert report["budget_comparison"]["monthly_budget"] == 0
    assert report["category_spending"] == []


def test_report_cli_command_renders_sections(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()

    BudgetService().set_budget(30000)
    IncomeService().add_income("Salary", 45000)
    ExpenseService().add_expense(5000, "Housing")

    runner = CliRunner()
    result = runner.invoke(app, ["report"])

    assert result.exit_code == 0
    assert "Income vs Expense" in result.output
    assert "Expense Breakdown" in result.output
    assert "Budget Comparison" in result.output
    assert "Category Spending" in result.output
