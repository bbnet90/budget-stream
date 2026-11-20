from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import __version__
from .budget_service import BudgetService
from .category_service import CategoryService
from .dashboard_service import DashboardService
from .db import initialize_database
from .expense_service import ExpenseService
from .income_service import IncomeService
from .recurring_service import RecurringService
from .report_service import ReportService
from .services import current_month_label

app = typer.Typer(
    help="Personal finance CLI for budgets, income, expenses, and recurring transactions.",
    add_completion=False,
    invoke_without_command=True,
)

console = Console(markup=False, emoji=False)


@contextmanager
def command_database():
    try:
        initialize_database()
        yield
    except (ValueError, sqlite3.Error, OSError) as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


def version_callback(value: bool):
    if value:
        typer.echo(f"wallet {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
):
    if ctx.invoked_subcommand is None:
        render_dashboard()


@app.command("dashboard", help="Show the current monthly dashboard summary.")
def dashboard():
    render_dashboard()


@app.command("report", help="Show the current month income, expense, and budget summary.")
def report():
    with command_database():
        report_data = ReportService().get_current_report()

    income_vs_expense = Table(title="Income vs Expense")
    income_vs_expense.add_column("Metric", style="cyan")
    income_vs_expense.add_column("Value", style="green", justify="right")
    income_vs_expense.add_row("Total Income", f"{report_data['income_vs_expense']['total_income']:,.2f}")
    income_vs_expense.add_row("Total Expenses", f"{report_data['income_vs_expense']['total_expenses']:,.2f}")
    income_vs_expense.add_row("Net Cash Flow", f"{report_data['income_vs_expense']['net_cash_flow']:,.2f}")
    income_vs_expense.add_row("Expense-to-Income %", f"{report_data['income_vs_expense']['expense_to_income_percentage']:.2f}%")
    console.print(income_vs_expense)

    expense_breakdown = Table(title="Expense Breakdown")
    expense_breakdown.add_column("Metric", style="cyan")
    expense_breakdown.add_column("Value", style="green", justify="right")
    expense_breakdown.add_row("Required Expenses", f"{report_data['expense_breakdown']['required_expenses']:,.2f}")
    expense_breakdown.add_row("Discretionary Expenses", f"{report_data['expense_breakdown']['discretionary_expenses']:,.2f}")
    expense_breakdown.add_row("Required Share %", f"{report_data['expense_breakdown']['required_share_percentage']:.2f}%")
    expense_breakdown.add_row("Discretionary Share %", f"{report_data['expense_breakdown']['discretionary_share_percentage']:.2f}%")
    console.print(expense_breakdown)

    budget_comparison = Table(title="Budget Comparison")
    budget_comparison.add_column("Metric", style="cyan")
    budget_comparison.add_column("Value", style="green", justify="right")
    budget_comparison.add_row("Monthly Budget", f"{report_data['budget_comparison']['monthly_budget']:,.2f}")
    budget_comparison.add_row("Total Expenses", f"{report_data['budget_comparison']['total_expenses']:,.2f}")
    budget_comparison.add_row("Remaining Budget", f"{report_data['budget_comparison']['remaining_budget']:,.2f}")
    budget_comparison.add_row("Budget Usage %", f"{report_data['budget_comparison']['budget_usage_percentage']:.2f}%")
    console.print(budget_comparison)

    if report_data["category_spending"]:
        category_table = Table(title="Category Spending")
        category_table.add_column("Category", style="cyan")
        category_table.add_column("Amount", style="green", justify="right")
        category_table.add_column("% of Total", style="magenta", justify="right")

        for item in report_data["category_spending"]:
            category_table.add_row(
                item["category"],
                f"{item['amount']:,.2f}",
                f"{item['percentage_of_total_expenses']:.2f}%",
            )

        console.print(category_table)
    else:
        console.print("No expenses recorded for the current month.")


def render_dashboard() -> None:
    with command_database():
        summary = DashboardService().get_monthly_summary()
    month_label = summary["month_label"]

    summary_lines = [
        "[bold]BudgetStream[/bold]",
        month_label,
        "",
        f"Total income: {summary['total_income']:,.2f}",
        f"Monthly budget: {summary['budget']:,.2f}",
        f"Total expenses: {summary['total_expenses']:,.2f}",
        f"Expense Count: {summary['expense_count']}",
        f"Budget Usage: {summary['budget_usage_percentage']:.1f}%",
        f"Remaining budget: {summary['remaining_budget']:,.2f}",
        f"Days Remaining: {summary['days_remaining']}",
        f"Daily Available: {summary['daily_available']:,.2f}",
        f"Required expenses: {summary['required_expenses']:,.2f}",
        f"Discretionary expenses: {summary['discretionary_expenses']:,.2f}",
    ]

    console.print(Panel.fit(Text.from_markup("\n".join(summary_lines)), border_style="green"))

    if summary["category_totals"]:
        category_table = Table(title="Category totals")
        category_table.add_column("Category", style="cyan")
        category_table.add_column("Total", style="green", justify="right")
        for item in summary["category_totals"]:
            category_table.add_row(item["category"], f"{item['total']:,.2f}")
        console.print(category_table)

    if summary["recent_expenses"]:
        expense_table = Table(title="Recent expenses")
        expense_table.add_column("Date")
        expense_table.add_column("Category", style="cyan")
        expense_table.add_column("Amount", style="magenta", justify="right")
        expense_table.add_column("Required")
        for item in summary["recent_expenses"]:
            expense_table.add_row(
                item["date"],
                item["category"],
                f"{item['amount']:,.2f}",
                "Yes" if item["is_required"] else "No",
            )
        console.print(expense_table)


category_app = typer.Typer(help="Manage spending categories used by expenses.")
app.add_typer(category_app, name="category")


@category_app.command("list")
def category_list():
    with command_database():
        categories = CategoryService().list_categories()

    if not categories:
        console.print("No categories found.")
        return

    table = Table(title="Categories")
    table.add_column("Name", style="cyan")
    table.add_column("Kind", style="magenta")
    table.add_column("Default", style="green")

    for category in categories:
        table.add_row(
            category["name"],
            category["kind"].title(),
            "Yes" if category["is_default"] else "No",
        )

    console.print(table)


@category_app.command("add")
def category_add(
    name: str = typer.Option(..., "--name", help="Category name."),
    kind: str = typer.Option(..., "--kind", help="Category kind: required or discretionary."),
):
    with command_database():
        category = CategoryService().add_category(name, kind)

    typer.secho(f'✓ Category "{category["name"]}" added.', fg=typer.colors.GREEN)


@category_app.command("remove")
def category_remove(
    name: str = typer.Option(..., "--name", help="Category name to remove."),
):
    with command_database():
        CategoryService().delete_category(name)

    typer.secho(f'✓ Category "{name}" removed.', fg=typer.colors.GREEN)


budget_app = typer.Typer(help="Set and view the current month's budget.")
app.add_typer(budget_app, name="budget")


@budget_app.command("set")
def budget_set(
    amount: float = typer.Option(..., "--amount", help="Monthly budget amount."),
):
    with command_database():
        budget = BudgetService().set_budget(amount)

    month_label = current_month_label()
    typer.secho(f'✓ Monthly budget set for {month_label}: {budget["monthly_budget"]:,.2f}', fg=typer.colors.GREEN)


@budget_app.command("show")
def budget_show():
    with command_database():
        budget = BudgetService().get_current_budget()

    if budget is None:
        typer.secho(f"No budget is set for {current_month_label()}.", fg=typer.colors.YELLOW)
        return

    table = Table(title="Monthly Budget")
    table.add_column("Month", style="cyan")
    table.add_column("Budget", style="green", justify="right")
    table.add_row(current_month_label(), f"{budget['monthly_budget']:,.2f}")
    console.print(table)


income_app = typer.Typer(help="Record and review monthly income.")
app.add_typer(income_app, name="income")


@income_app.command("add")
def income_add(
    source: str = typer.Option(..., "--source", help="Income source name."),
    amount: float = typer.Option(..., "--amount", help="Income amount."),
):
    with command_database():
        income = IncomeService().add_income(source, amount)

    typer.secho(
        f'✓ Income added for {income["source_name"]}: {income["amount"]:,.2f}',
        fg=typer.colors.GREEN,
    )


@income_app.command("list")
def income_list():
    with command_database():
        entries = IncomeService().list_current_month_income()

    if not entries:
        typer.secho(f"No income entries for {current_month_label()}.", fg=typer.colors.YELLOW)
        return

    table = Table(title="Income")
    table.add_column("Source", style="cyan")
    table.add_column("Amount", style="green", justify="right")

    for entry in entries:
        table.add_row(entry["source_name"], f"{entry['amount']:,.2f}")

    console.print(table)


expense_app = typer.Typer(help="Record and review monthly expenses.")
app.add_typer(expense_app, name="expense")


@expense_app.command("add")
def expense_add(
    amount: float = typer.Option(..., "--amount", help="Expense amount."),
    category: str = typer.Option(..., "--category", help="Existing category name."),
    description: Optional[str] = typer.Option(None, "--description", help="Optional expense description."),
):
    with command_database():
        expense = ExpenseService().add_expense(amount, category, description=description)

    typer.secho(
        f'✓ Expense added: {expense["amount"]:,.2f} — {expense["category_name"]}',
        fg=typer.colors.GREEN,
    )


@expense_app.command("list")
def expense_list():
    with command_database():
        expenses = ExpenseService().list_current_month_expenses()

    if not expenses:
        typer.secho(f"No expenses for {current_month_label()}.", fg=typer.colors.YELLOW)
        return

    table = Table(title="Expenses")
    table.add_column("ID", justify="right")
    table.add_column("Date")
    table.add_column("Category", style="cyan")
    table.add_column("Amount", justify="right", style="magenta")
    table.add_column("Description")
    table.add_column("Required")

    for expense in expenses:
        table.add_row(
            str(expense["id"]),
            expense["expense_date"],
            expense["category_name"],
            f"{expense['amount']:,.2f}",
            expense["description"] or "",
            "Yes" if expense["is_required"] else "No",
        )

    console.print(table)


@expense_app.command("delete")
def expense_delete(
    expense_id: int = typer.Option(..., "--id", help="Expense ID to delete."),
):
    with command_database():
        ExpenseService().delete_expense(expense_id)

    typer.secho(f"✓ Expense #{expense_id} deleted.", fg=typer.colors.GREEN)


recurring_app = typer.Typer(help="Create, review, and apply recurring income or expense definitions.")
app.add_typer(recurring_app, name="recurring")


@recurring_app.command("add")
def recurring_add(
    type_: str = typer.Option(..., "--type", help="income or expense"),
    source: Optional[str] = typer.Option(None, "--source", help="Income source name."),
    category: Optional[str] = typer.Option(None, "--category", help="Expense category name."),
    amount: float = typer.Option(..., "--amount", help="Recurring amount."),
    description: Optional[str] = typer.Option(None, "--description", help="Optional recurring description."),
    frequency: str = typer.Option("monthly", "--frequency", help="Recurring cadence."),
    next_run: str = typer.Option(..., "--next-run", help="Next run date in YYYY-MM-DD format."),
):
    with command_database():
        entry = RecurringService().add_recurring(
            type_=type_,
            source_name=source,
            category_name=category,
            amount=amount,
            description=description,
            frequency=frequency,
            next_run_date=next_run,
        )

    label = entry["source_name"] or entry["category_name"] or entry["description"] or "Recurring"
    typer.secho(f'✓ Recurring {entry["type"]} added: {label}', fg=typer.colors.GREEN)


@recurring_app.command("list")
def recurring_list():
    with command_database():
        entries = RecurringService().list_recurring()

    if not entries:
        typer.secho("No recurring transactions configured.", fg=typer.colors.YELLOW)
        return

    table = Table(title="Recurring Transactions")
    table.add_column("ID", justify="right")
    table.add_column("Type", style="cyan")
    table.add_column("Source / Category", style="magenta")
    table.add_column("Amount", justify="right", style="green")
    table.add_column("Next Run", style="yellow")
    table.add_column("Status")

    for entry in entries:
        name = entry["source_name"] or entry["category_name"] or "-"
        status = "Active" if entry["is_active"] else "Inactive"
        table.add_row(
            str(entry["id"]),
            entry["type"].title(),
            name,
            f"{entry['amount']:,.2f}",
            entry["next_run_date"],
            status,
        )

    console.print(table)


@recurring_app.command("enable")
def recurring_enable(
    recurring_id: int = typer.Option(..., "--id", help="Recurring ID to enable."),
):
    with command_database():
        RecurringService().enable_recurring(recurring_id)

    typer.secho(f"✓ Recurring #{recurring_id} enabled.", fg=typer.colors.GREEN)


@recurring_app.command("disable")
def recurring_disable(
    recurring_id: int = typer.Option(..., "--id", help="Recurring ID to disable."),
):
    with command_database():
        RecurringService().disable_recurring(recurring_id)

    typer.secho(f"✓ Recurring #{recurring_id} disabled.", fg=typer.colors.GREEN)


@recurring_app.command("delete")
def recurring_delete(
    recurring_id: int = typer.Option(..., "--id", help="Recurring ID to delete."),
):
    with command_database():
        RecurringService().delete_recurring(recurring_id)

    typer.secho(f"✓ Recurring #{recurring_id} deleted.", fg=typer.colors.GREEN)


@recurring_app.command("apply")
def recurring_apply():
    with command_database():
        applied = RecurringService().apply_due_recurring()
    if not applied:
        typer.secho("No recurring transactions were due to apply; nothing was applied.", fg=typer.colors.YELLOW)
        return

    count = len(applied)
    typer.secho(f"✓ Applied {count} recurring transaction(s).", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
