from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .budget_service import BudgetService
from .category_service import CategoryService
from .dashboard_service import DashboardService
from .db import initialize_database
from .expense_service import ExpenseService
from .income_service import IncomeService
from .services import current_month_label

app = typer.Typer(
    help="Personal budget management CLI.",
    add_completion=False,
    invoke_without_command=True,
)

console = Console()


def version_callback(value: bool):
    if value:
        typer.echo(f"wallet {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
):
    if ctx.invoked_subcommand is None:
        render_dashboard()


@app.command("dashboard")
def dashboard():
    render_dashboard()


def render_dashboard() -> None:
    initialize_database()
    summary = DashboardService().get_monthly_summary()
    month_label = summary["month_label"]

    summary_lines = [
        "[bold]BudgetStream[/bold]",
        month_label,
        "",
        f"Total income: {summary['total_income']:,.0f}",
        f"Monthly budget: {summary['budget']:,.0f}",
        f"Total expenses: {summary['total_expenses']:,.0f}",
        f"Expense Count: {summary['expense_count']}",
        f"Budget Usage: {summary['budget_usage_percentage']:.1f}%",
        f"Remaining budget: {summary['remaining_budget']:,.0f}",
        f"Required expenses: {summary['required_expenses']:,.0f}",
        f"Discretionary expenses: {summary['discretionary_expenses']:,.0f}",
    ]

    console.print(Panel.fit("\n".join(summary_lines), border_style="green"))

    if summary["category_totals"]:
        category_table = Table(title="Category totals")
        category_table.add_column("Category", style="cyan")
        category_table.add_column("Total", style="green", justify="right")
        for item in summary["category_totals"]:
            category_table.add_row(item["category"], f"{item['total']:,.0f}")
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
                f"{item['amount']:,.0f}",
                "Yes" if item["is_required"] else "No",
            )
        console.print(expense_table)


category_app = typer.Typer(help="Manage expense categories.")
app.add_typer(category_app, name="category")


@category_app.command("list")
def category_list():
    initialize_database()
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
    initialize_database()

    try:
        category = CategoryService().add_category(name, kind)
    except ValueError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.secho(f'✓ Category "{category["name"]}" added.', fg=typer.colors.GREEN)


@category_app.command("remove")
def category_remove(
    name: str = typer.Option(..., "--name", help="Category name to remove."),
):
    initialize_database()

    try:
        CategoryService().delete_category(name)
    except ValueError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.secho(f'✓ Category "{name}" removed.', fg=typer.colors.GREEN)


budget_app = typer.Typer(help="Manage the monthly budget.")
app.add_typer(budget_app, name="budget")


@budget_app.command("set")
def budget_set(
    amount: float = typer.Option(..., "--amount", help="Monthly budget amount."),
):
    initialize_database()

    try:
        budget = BudgetService().set_budget(amount)
    except ValueError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    month_label = current_month_label()
    typer.secho(f'✓ Monthly budget set for {month_label}: {budget["monthly_budget"]:,.0f}', fg=typer.colors.GREEN)


@budget_app.command("show")
def budget_show():
    initialize_database()
    budget = BudgetService().get_current_budget()

    if budget is None:
        typer.secho(f"No budget is set for {current_month_label()}.", fg=typer.colors.YELLOW)
        return

    table = Table(title="Monthly Budget")
    table.add_column("Month", style="cyan")
    table.add_column("Budget", style="green", justify="right")
    table.add_row(current_month_label(), f"{budget['monthly_budget']:,.0f}")
    console.print(table)


income_app = typer.Typer(help="Manage monthly income.")
app.add_typer(income_app, name="income")


@income_app.command("add")
def income_add(
    source: str = typer.Option(..., "--source", help="Income source name."),
    amount: float = typer.Option(..., "--amount", help="Income amount."),
):
    initialize_database()

    try:
        income = IncomeService().add_income(source, amount)
    except ValueError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.secho(
        f'✓ Income added for {income["source_name"]}: {income["amount"]:,.0f}',
        fg=typer.colors.GREEN,
    )


@income_app.command("list")
def income_list():
    initialize_database()
    entries = IncomeService().list_current_month_income()

    if not entries:
        typer.secho(f"No income entries for {current_month_label()}.", fg=typer.colors.YELLOW)
        return

    table = Table(title="Income")
    table.add_column("Source", style="cyan")
    table.add_column("Amount", style="green", justify="right")

    for entry in entries:
        table.add_row(entry["source_name"], f"{entry['amount']:,.0f}")

    console.print(table)


expense_app = typer.Typer(help="Manage monthly expenses.")
app.add_typer(expense_app, name="expense")


@expense_app.command("add")
def expense_add(
    amount: float = typer.Option(..., "--amount", help="Expense amount."),
    category: str = typer.Option(..., "--category", help="Existing category name."),
    description: Optional[str] = typer.Option(None, "--description", help="Optional expense description."),
):
    initialize_database()

    try:
        expense = ExpenseService().add_expense(amount, category, description=description)
    except ValueError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.secho(
        f'✓ Expense added: {expense["amount"]:,.0f} — {expense["category_name"]}',
        fg=typer.colors.GREEN,
    )


@expense_app.command("list")
def expense_list():
    initialize_database()
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
            f"{expense['amount']:,.0f}",
            expense["description"] or "",
            "Yes" if expense["is_required"] else "No",
        )

    console.print(table)


@expense_app.command("delete")
def expense_delete(
    expense_id: int = typer.Option(..., "--id", help="Expense ID to delete."),
):
    initialize_database()

    try:
        ExpenseService().delete_expense(expense_id)
    except ValueError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.secho(f"✓ Expense #{expense_id} deleted.", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
