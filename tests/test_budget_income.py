import sqlite3

import pytest

from wallet.budget_service import BudgetService
from wallet.income_service import IncomeService
from wallet.db import initialize_database
from wallet.services import current_month_key


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "wallet.db"
    monkeypatch.setenv("WALLET_DB_PATH", str(db_path))
    initialize_database()
    return db_path


def test_budget_can_be_created_for_current_month(isolated_db):
    service = BudgetService()
    budget = service.set_budget(30000)

    assert budget["monthly_budget"] == 30000
    assert budget["month"] == current_month_key()


def test_budget_amount_is_stored_correctly(isolated_db):
    service = BudgetService()
    service.set_budget(25000)

    saved = service.get_current_budget()
    assert saved is not None
    assert saved["monthly_budget"] == 25000


def test_setting_budget_twice_updates_instead_of_duplication(isolated_db):
    service = BudgetService()
    service.set_budget(30000)
    service.set_budget(35000)

    with sqlite3.connect(isolated_db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM budgets WHERE month = ?", (current_month_key(),)).fetchone()[0]
        total = conn.execute("SELECT monthly_budget FROM budgets WHERE month = ?", (current_month_key(),)).fetchone()[0]

    assert count == 1
    assert total == 35000


def test_invalid_budget_amount_is_rejected(isolated_db):
    service = BudgetService()

    with pytest.raises(ValueError, match="greater than 0"):
        service.set_budget(0)


def test_showing_budget_when_none_exists_is_handled_cleanly(isolated_db):
    service = BudgetService()

    assert service.get_current_budget() is None


def test_income_can_be_added(isolated_db):
    service = IncomeService()
    income = service.add_income("Salary", 45000)

    assert income["source_name"] == "Salary"
    assert income["amount"] == 45000
    assert income["month"] == current_month_key()


def test_income_source_is_stored_correctly(isolated_db):
    service = IncomeService()
    service.add_income("Freelance", 3000)

    entries = service.list_current_month_income()
    assert entries[0]["source_name"] == "Freelance"


def test_income_amount_is_stored_correctly(isolated_db):
    service = IncomeService()
    service.add_income("Bonus", 1500)

    entries = service.list_current_month_income()
    assert entries[0]["amount"] == 1500


def test_multiple_income_entries_can_exist(isolated_db):
    service = IncomeService()
    service.add_income("Salary", 45000)
    service.add_income("Bonus", 2500)

    entries = service.list_current_month_income()
    assert len(entries) == 2


def test_non_positive_income_is_rejected(isolated_db):
    service = IncomeService()

    with pytest.raises(ValueError, match="greater than 0"):
        service.add_income("Salary", 0)


def test_current_month_income_listing_works(isolated_db):
    service = IncomeService()
    service.add_income("Salary", 45000)
    service.add_income("Side gig", 4000)

    entries = service.list_current_month_income()
    assert len(entries) == 2
    assert {row["source_name"] for row in entries} == {"Salary", "Side gig"}


def test_empty_income_listing_is_handled_cleanly(isolated_db):
    service = IncomeService()

    assert service.list_current_month_income() == []
