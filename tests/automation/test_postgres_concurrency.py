"""Real PostgreSQL concurrency invariant checks using disposable tables.

Opt in: export TEST_DATABASE_URL pointing to a disposable PostgreSQL database,
then `python -m pytest tests/automation/test_postgres_concurrency.py -q`. Never run on production database.
Tests model SQL row-locking / idempotency invariants, not the full HTTP Saga.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='TEST_DATABASE_URL not set (requires disposable PostgreSQL DB)')

@pytest.fixture
def database():
    engine = create_engine(os.environ['TEST_DATABASE_URL'], pool_size=8)
    if engine.dialect.name != 'postgresql':
        pytest.skip('Requires PostgreSQL row-level locks')
    with engine.begin() as conn:
        conn.execute(text('CREATE TEMP TABLE _unused_test (id integer)'))
    # Unique randomly named tables allow concurrent test runs without touching application tables.
    import uuid
    suffix = uuid.uuid4().hex[:12]
    wallet, tuition, ledger = [f'test_{kind}_{suffix}' for kind in ('wallet','tuition','ledger')]
    with engine.begin() as conn:
        conn.execute(text(f'CREATE TABLE {wallet} (id int PRIMARY KEY, balance numeric(18,2) NOT NULL CHECK(balance >= 0))'))
        conn.execute(text(f'CREATE TABLE {tuition} (id int PRIMARY KEY, paid_by text UNIQUE)'))
        conn.execute(text(f'CREATE TABLE {ledger} (txn text PRIMARY KEY)'))
        conn.execute(text(f'INSERT INTO {wallet} VALUES (1, 100)'))
        conn.execute(text(f'INSERT INTO {tuition} VALUES (1, NULL)'))
    try:
        yield engine, wallet, tuition, ledger
    finally:
        with engine.begin() as conn:
            for table in (ledger,tuition,wallet):
                conn.execute(text(f'DROP TABLE IF EXISTS {table}'))
        engine.dispose()


def test_simultaneous_debits_cannot_overdraw(database):
    engine, wallet, _, ledger = database
    def debit(txn):
        with engine.begin() as conn:
            row = conn.execute(text(f'SELECT balance FROM {wallet} WHERE id=1 FOR UPDATE')).scalar_one()
            if row < 80:
                return False
            conn.execute(text(f'UPDATE {wallet} SET balance=balance-80 WHERE id=1'))
            conn.execute(text(f'INSERT INTO {ledger} VALUES (:id)'), {'id':txn})
            return True
    with ThreadPoolExecutor(max_workers=2) as pool:
        successes=list(pool.map(debit,['a','b']))
    assert successes.count(True)==1
    with engine.connect() as conn:
        assert conn.execute(text(f'SELECT balance FROM {wallet} WHERE id=1')).scalar_one()==Decimal('20')


def test_simultaneous_tuition_settlement_only_one_wins(database):
    engine, _, tuition, _ = database
    def pay(txn):
        with engine.begin() as conn:
            paid = conn.execute(text(f'SELECT paid_by FROM {tuition} WHERE id=1 FOR UPDATE')).scalar_one()
            if paid is not None:
                return paid == txn
            conn.execute(text(f'UPDATE {tuition} SET paid_by=:txn WHERE id=1'), {'txn': txn})
            return True
    with ThreadPoolExecutor(max_workers=2) as pool:
        successes=list(pool.map(pay,['a','b']))
    assert successes.count(True)==1
