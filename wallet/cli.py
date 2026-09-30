from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .category_service import CategoryService
from .db import initialize_database
from .services import current_month_label, get_dashboard_snapshot

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
        initialize_database()
        snapshot = get_dashboard_snapshot()
        month_label = snapshot["month_label"]

        if not snapshot["budget_configured"]:
            console.print(Panel.fit(
                f"[bold]BudgetStream[/bold]\n{month_label}\n\n[yellow]No budget configured yet.[/yellow]\n[dim]Use 'wallet budget set --amount 3000' to begin.[/dim]",
                border_style="cyan",
            ))
            return

        console.print(Panel.fit(
            f"[bold]BudgetStream[/bold]\n{month_label}\n\nBudget: {snapshot['budget_amount']}\n[dim]Monthly budget is configured.[/dim]",
            border_style="green",
        ))


@app.command("dashboard")
def dashboard():
    initialize_database()
    snapshot = get_dashboard_snapshot()
    month_label = snapshot["month_label"]

    if not snapshot["budget_configured"]:
        console.print(Panel.fit(
            f"[bold]BudgetStream[/bold]\n{month_label}\n\n[yellow]No budget configured yet.[/yellow]\n[dim]Use 'wallet budget set --amount 3000' to begin.[/dim]",
            border_style="cyan",
        ))
        return

    console.print(Panel.fit(
        f"[bold]BudgetStream[/bold]\n{month_label}\n\nBudget: {snapshot['budget_amount']}\n[dim]Monthly budget is configured.[/dim]",
        border_style="green",
    ))


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


if __name__ == "__main__":
    app()
