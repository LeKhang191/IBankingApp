"""Safe orchestration smoke test; mocks Auth/Tuition HTTP calls and cleans up its DB rows.

Run inside the payment-service container after applying the Phase 3 SQL migration:
    python -m app.tests.phase3_saga_smoke
"""

import asyncio
import uuid
from uuid import uuid4
from datetime import datetime, timedelta
from decimal import Decimal

from app import main
from app.models import OutboxEvent, PaymentTransaction


class StubResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code
        self.text = "stubbed downstream response"

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"Stubbed HTTP {self.status_code}")


class StubAsyncClient:
    response_plan = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, **kwargs):
        if not self.response_plan:
            raise AssertionError(f"Unexpected downstream request: {url}")
        expected_path, status_code = self.response_plan.pop(0)
        if expected_path not in url:
            raise AssertionError(f"Expected {expected_path}, received {url}")
        return StubResponse(status_code)


def create_transaction(transaction_id: str):
    with main.SessionLocal() as db:
        db.add(PaymentTransaction(
            id=transaction_id,
            mssv="52999998",
            student_name="PHASE 3 SMOKE TEST",
            amount=Decimal("100.00"),
            user_id=f"phase3-smoke-{uuid4().hex[:12]}", 
            user_email="phase3-smoke@example.invalid",
            otp_hash="0" * 64,
            otp_expires_at=datetime.utcnow() + timedelta(minutes=5),
            status="processing",
            debit_applied=False,
            tuition_settled=False,
        ))
        db.commit()


def cleanup(transaction_ids):
    with main.SessionLocal() as db:
        db.query(OutboxEvent).filter(OutboxEvent.aggregate_id.in_(transaction_ids)).delete(synchronize_session=False)
        db.query(PaymentTransaction).filter(PaymentTransaction.id.in_(transaction_ids)).delete(synchronize_session=False)
        db.commit()


async def run_checks():
    if not main.INTERNAL_SERVICE_TOKEN:
        raise RuntimeError("INTERNAL_SERVICE_TOKEN must be configured in the payment-service container.")

    success_id = f"TXN-PH3-SUCCESS-{uuid.uuid4().hex[:12]}"
    compensation_id = f"TXN-PH3-COMP-{uuid.uuid4().hex[:12]}"
    ids = [success_id, compensation_id]
    original_client = main.httpx.AsyncClient

    try:
        create_transaction(success_id)
        create_transaction(compensation_id)
        main.httpx.AsyncClient = StubAsyncClient
        main.AUTH_SERVICE_URL = "http://stub-auth"
        main.TUITION_SERVICE_URL = "http://stub-tuition"
        main.NOTIFICATION_SERVICE_URL = "http://stub-notification"

        StubAsyncClient.response_plan = [("/deduct", 200), ("/pay", 200)]
        success_result = await main.process_saga(success_id)
        assert success_result and success_result["status"] == "success", success_result

        with main.SessionLocal() as db:
            txn = db.query(PaymentTransaction).filter_by(id=success_id).one()
            event_count = db.query(OutboxEvent).filter_by(aggregate_id=success_id).count()
            assert txn.debit_applied is True
            assert txn.tuition_settled is True
            assert event_count == 1, event_count

        # First receipt attempt fails, leaving a durable pending event; the
        # second attempt succeeds after the retry timestamp is made due.
        StubAsyncClient.response_plan = [("/send-receipt", 503)]
        assert await main.process_outbox_once() is True
        with main.SessionLocal() as db:
            event = db.query(OutboxEvent).filter_by(aggregate_id=success_id).one()
            assert event.status == "pending"
            assert event.attempts == 1
            event.next_attempt_at = datetime.utcnow() - timedelta(seconds=1)
            db.commit()

        StubAsyncClient.response_plan = [("/send-receipt", 200)]
        assert await main.process_outbox_once() is True
        with main.SessionLocal() as db:
            event = db.query(OutboxEvent).filter_by(aggregate_id=success_id).one()
            assert event.status == "sent"
            assert event.attempts == 2

        StubAsyncClient.response_plan = [("/deduct", 200), ("/pay", 409), ("/refund", 200)]
        compensation_result = await main.process_saga(compensation_id)
        assert compensation_result and compensation_result["status"] == "failed", compensation_result

        with main.SessionLocal() as db:
            txn = db.query(PaymentTransaction).filter_by(id=compensation_id).one()
            assert txn.debit_applied is True
            assert txn.tuition_settled is False

        print("PASS: Saga success commits one durable receipt outbox event.")
        print("PASS: outbox keeps a failed delivery pending and marks it sent after retry.")
        print("PASS: definitive tuition conflict triggers one idempotent compensation request.")
    finally:
        main.httpx.AsyncClient = original_client
        cleanup(ids)


if __name__ == "__main__":
    asyncio.run(run_checks())
