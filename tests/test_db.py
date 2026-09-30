import sqlite3

from wallet.config import get_db_path
from wallet.db import initialize_database


def test_database_initialization_creates_schema(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))

    initialize_database()

    assert db_path.exists()

    with sqlite3.connect(db_path) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()

    table_names = {row[0] for row in tables}
    assert {"budgets", "income", "categories", "expenses"}.issubset(table_names)


def test_get_db_path_uses_default_when_not_configured(monkeypatch):
    monkeypatch.delenv("WALLET_DB_PATH", raising=False)
    db_path = get_db_path()
    assert db_path.name == "wallet.db"
    assert "wallet" in str(db_path)
