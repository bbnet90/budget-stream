# BudgetStream

BudgetStream is a personal finance and budgeting CLI built with Python, Typer, Rich, and SQLite. It helps you track monthly budgets, income, expenses, category spending, and recurring financial transactions from the terminal.

## Features

- Monthly budget tracking
- Income tracking by month
- Expense tracking with category assignment
- Required vs. discretionary expense categories
- Financial dashboard summary
- Daily available money calculation
- Budget and category reports
- Recurring transaction definitions and manual application

## Requirements

- Python 3.11 or newer

## Installation

From the source checkout, install the package:

```bash
python -m pip install .
```

## Usage

Run the CLI without arguments to open the dashboard.

```bash
wallet
```

Common examples include the following commands.

```bash
wallet
wallet category list
wallet category add --name Insurance --kind required
wallet budget set --amount 30000
wallet income add --source "Salary" --amount 45000
wallet expense add --amount 500 --category Food
wallet report
wallet recurring list
```

To create a monthly expense, choose its first due date and apply it when due:

```bash
wallet recurring add --type expense --category Insurance --amount 125.50 --next-run 2026-12-01
wallet recurring apply
```

`wallet recurring apply` posts each missed monthly occurrence through today. Each occurrence uses its scheduled month. If a month is too short for the scheduled day, the schedule moves to its last day and continues from that day in subsequent months.

## Data storage

BudgetStream stores data in a local SQLite database. By default, it creates a database in your home directory under `.wallet/wallet.db` unless `WALLET_DB_PATH` is set.

## Testing

Install the development extra and run the test suite from the checkout:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Project structure

- `wallet/` — CLI, services, repositories, and database bootstrapping
- `tests/` — automated validation for dashboard, reports, expenses, budgets, income, and recurring transactions
- `pyproject.toml` — project metadata and packaging configuration

## License

BudgetStream is available under the [MIT License](LICENSE).
