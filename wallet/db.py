import sqlite3
from pathlib import Path

from .config import get_db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT NOT NULL UNIQUE,
    monthly_budget REAL NOT NULL DEFAULT 0 CHECK(monthly_budget >= 0),
    currency TEXT NOT NULL DEFAULT 'TRY',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS income (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT NOT NULL,
    source_name TEXT NOT NULL,
    amount REAL NOT NULL CHECK(amount >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL CHECK(kind IN ('required', 'discretionary')),
    is_default INTEGER NOT NULL DEFAULT 0 CHECK(is_default IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    amount REAL NOT NULL CHECK(amount > 0),
    description TEXT,
    expense_date TEXT NOT NULL,
    is_required INTEGER NOT NULL DEFAULT 0 CHECK(is_required IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(category_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS recurring_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
    source_name TEXT,
    category_id INTEGER,
    amount REAL NOT NULL CHECK(amount > 0),
    description TEXT,
    frequency TEXT NOT NULL CHECK(frequency = 'monthly'),
    next_run_date TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(category_id) REFERENCES categories(id)
);
"""


DEFAULT_CATEGORIES = [
    ("Food", "discretionary"),
    ("Housing", "required"),
    ("Rent", "required"),
    ("Utilities", "required"),
    ("Transport", "discretionary"),
    ("Health", "required"),
    ("Entertainment", "discretionary"),
    ("Shopping", "discretionary"),
    ("Savings", "required"),
    ("Other", "discretionary"),
]


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(get_db_path())
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def initialize_database() -> Path:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.executescript(SCHEMA)

        for name, kind in DEFAULT_CATEGORIES:
            connection.execute(
                "INSERT OR IGNORE INTO categories (name, kind, is_default) VALUES (?, ?, 1)",
                (name, kind),
            )

        connection.commit()

    return db_path
