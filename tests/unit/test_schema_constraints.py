"""Offline schema contract tests: load each service models in an isolated module namespace.
Does not require PostgreSQL, SMTP, or network access.
"""
import importlib.util
import sys
import types
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base

ROOT = Path(__file__).resolve().parents[2]


def load_models(service):
    # Avoid collision between the separate `app` Python packages.
    original_app = sys.modules.get("app")
    original_database = sys.modules.get("app.database")
    package = types.ModuleType("app")
    package.__path__ = []
    database = types.ModuleType("app.database")
    database.Base = declarative_base()
    sys.modules["app"] = package
    sys.modules["app.database"] = database
    try:
        filename = ROOT / "backend" / service / "app" / "models.py"
        spec = importlib.util.spec_from_file_location("isolated_models", filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, "Base", database.Base)
    finally:
        if original_app is None:
            sys.modules.pop("app", None)
        else:
            sys.modules["app"] = original_app
        if original_database is None:
            sys.modules.pop("app.database", None)
        else:
            sys.modules["app.database"] = original_database


@pytest.mark.parametrize("service,expected", [
    ("auth-service", {"users", "wallet_operations"}),
    ("tuition-service", {"tuitions"}),
    ("payment-service", {"transactions", "outbox_events"}),
])
def test_service_owned_schema_and_constraints(service, expected):
    base = load_models(service)
    engine = create_engine("sqlite+pysqlite:///:memory:")
    base.metadata.create_all(engine)
    assert set(inspect(engine).get_table_names()) == expected
    with engine.begin() as conn:
        if service == "auth-service":
            import sqlalchemy
            with pytest.raises(sqlalchemy.exc.IntegrityError):
                conn.execute(text("INSERT INTO users (id,username,hashed_password,name,email,balance) VALUES ('x','x','hash','Test','a@b.test',-1)"))
        elif service == "tuition-service":
            import sqlalchemy
            with pytest.raises(sqlalchemy.exc.IntegrityError):
                conn.execute(text("INSERT INTO tuitions (student_code,student_name,tuition_fee,is_paid) VALUES ('1','Test',-1,0)"))
        else:
            assert "ck_payments_positive_amount" in {c.name for c in base.metadata.tables['transactions'].constraints}


def test_api_gateway_routes_are_explicitly_mapped():
    config = (ROOT / "gateway/nginx.conf").read_text()
    for prefix in ("/api/auth/", "/api/tuitions/", "/api/payments/"):
        assert prefix in config
    assert "location ~ ^/api/auth/(deduct|refund)/?$ { return 404; }" in config


def test_active_payment_unique_index_blocks_duplicate_pending_rows():
    from sqlalchemy.exc import IntegrityError
    base = load_models("payment-service")
    engine = create_engine("sqlite+pysqlite:///:memory:")
    base.metadata.create_all(engine)
    columns = "id,mssv,student_name,amount,user_id,user_email,otp_hash,otp_expires_at,status,otp_attempts,otp_resend_count,is_verified,debit_applied,tuition_settled,saga_attempts,created_at"
    values = "(:id,'52123456','Test',100,'u1','a@example.test','hash','2030-01-01 00:00:00',:status,0,0,0,0,0,0,'2026-01-01 00:00:00')"
    with engine.begin() as conn:
        conn.execute(text(f"INSERT INTO transactions ({columns}) VALUES {values}"), {"id": "one", "status": "pending"})
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(text(f"INSERT INTO transactions ({columns}) VALUES {values}"), {"id": "two", "status": "processing"})
    with engine.begin() as conn:
        conn.execute(text("UPDATE transactions SET status='failed' WHERE id='one'"))
        conn.execute(text(f"INSERT INTO transactions ({columns}) VALUES {values}"), {"id": "two", "status": "pending"})
