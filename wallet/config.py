import os
from pathlib import Path


def get_db_path() -> Path:
    configured_path = os.getenv("WALLET_DB_PATH")
    if configured_path:
        return Path(configured_path).expanduser()

    return Path.home() / ".wallet" / "wallet.db"
