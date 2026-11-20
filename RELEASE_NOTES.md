# BudgetStream v0.1.0

The first public release of BudgetStream brings monthly budgeting, income and expense tracking, and spending reports to the terminal. The dashboard shows your remaining budget and daily available spending. You can define monthly recurring income and expenses, then apply due occurrences with `wallet recurring apply`.

BudgetStream requires Python 3.11 or newer. From the source checkout, install with `python -m pip install .`, then run `wallet --help`. The ledger is stored locally at `~/.wallet/wallet.db` by default.
