import os
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
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


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = db_path if db_path is not None else get_db_path()
    if str(path) not in ("", ":memory:"):
        # SQLite otherwise creates a new database with the process's default permissions.
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(descriptor)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


@contextmanager
def database_session(db_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    with closing(get_connection(db_path)) as connection, connection:
        yield connection


def initialize_database() -> Path:
    db_path = get_db_path()
    missing = []
    for directory in db_path.parents:
        if directory.is_dir():
            break
        missing.append(directory)
    for directory in reversed(missing):
        directory.mkdir(mode=0o700, exist_ok=True)

    with database_session(db_path) as connection:
        connection.executescript("BEGIN IMMEDIATE;\n" + SCHEMA)
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(categories)")}
        if "default_kind" in columns and "kind" not in columns:
            connection.execute("ALTER TABLE categories RENAME COLUMN default_kind TO kind")

        connection.executemany(
            """INSERT INTO categories (name, kind, is_default)
               SELECT :name, :kind, 1
               WHERE NOT EXISTS (SELECT 1 FROM categories WHERE name = :name)""",
            ({"name": name, "kind": kind} for name, kind in DEFAULT_CATEGORIES),
        )

    return db_path
