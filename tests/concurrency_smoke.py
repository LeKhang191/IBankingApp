"""Run against a disposable/demo deployment after setting the environment variables below.

This is an API-level concurrency smoke test, not a full pytest suite.
It restores the wallet balance after the debit test. The tuition test marks the
configured TEST_TUITION_MSSV as paid, so use a disposable unpaid test record.
"""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import httpx

AUTH_URL = os.getenv("AUTH_URL", "http://localhost:8000")
TUITION_URL = os.getenv("TUITION_URL", "http://localhost:8002")
USERNAME = os.environ["TEST_USERNAME"]
PASSWORD = os.environ["TEST_PASSWORD"]
INTERNAL_SERVICE_TOKEN = os.environ["INTERNAL_SERVICE_TOKEN"]
TEST_TUITION_MSSV = os.environ["TEST_TUITION_MSSV"]


def main():
    login = httpx.post(
        f"{AUTH_URL}/api/auth/login",
        json={"username": USERNAME, "password": PASSWORD},
        timeout=10,
    )
    login.raise_for_status()
    token = login.json()["token"]
    user_headers = {"Authorization": f"Bearer {token}"}
    me = httpx.get(f"{AUTH_URL}/api/auth/me", headers=user_headers, timeout=10)
    me.raise_for_status()
    user_id = str(me.json()["id"])
    balance = Decimal(str(me.json()["balance"]))
    internal_headers = {"X-Internal-Token": INTERNAL_SERVICE_TOKEN}
    test_amount = (balance * Decimal("0.70")).quantize(Decimal("0.01"))
    if test_amount <= 0:
        raise RuntimeError("Tài khoản kiểm thử cần có số dư lớn hơn 0.")

    debit_ids = [f"CONC-{uuid.uuid4().hex}" for _ in range(2)]

    def debit(txn_id):
        return httpx.post(
            f"{AUTH_URL}/api/auth/deduct",
            headers=internal_headers,
            json={"user_id": user_id, "amount": str(test_amount), "transaction_id": txn_id},
            timeout=15,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        debit_responses = list(pool.map(debit, debit_ids))

    successful_debits = [
        (txn_id, response)
        for txn_id, response in zip(debit_ids, debit_responses)
        if response.status_code == 200
    ]
    assert len(successful_debits) == 1, [r.status_code for r in debit_responses]

    # Restore the wallet after the concurrency assertion.
    successful_id, _ = successful_debits[0]
    refund = httpx.post(
        f"{AUTH_URL}/api/auth/refund",
        headers=internal_headers,
        json={"user_id": user_id, "amount": str(test_amount), "transaction_id": successful_id},
        timeout=15,
    )
    refund.raise_for_status()

    tuition_ids = [f"CONC-TUITION-{uuid.uuid4().hex}" for _ in range(2)]

    def settle(txn_id):
        return httpx.post(
            f"{TUITION_URL}/api/tuitions/{TEST_TUITION_MSSV}/pay",
            headers={"X-Internal-Token": INTERNAL_SERVICE_TOKEN},
            json={"transaction_id": txn_id},
            timeout=15,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        tuition_responses = list(pool.map(settle, tuition_ids))

    assert sorted(r.status_code for r in tuition_responses) == [200, 409], [
        (r.status_code, r.text) for r in tuition_responses
    ]

    print("PASS: concurrent wallet debit -> exactly one succeeds; balance was refunded.")
    print("PASS: concurrent tuition settlement -> exactly one transaction wins.")
    print("NOTE: TEST_TUITION_MSSV is now marked paid; use a disposable tuition row.")


if __name__ == "__main__":
    main()
