from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from . import __version__
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


if __name__ == "__main__":
    app()
