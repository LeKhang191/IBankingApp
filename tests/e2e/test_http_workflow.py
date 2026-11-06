"""Real HTTP checks. RUN ONLY on the isolated disposable Docker compose.e2e project.

These tests create and delete uniquely tagged rows in service-owned databases.
They exercise the actual FastAPI services and PostgreSQL through HTTP, not mock tables.
"""
import os
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import httpx
import pytest

REQUIRED_SENTINEL = "ONLY_ISOLATED_IBANKING_E2E"
pytestmark = pytest.mark.skipif(
    os.getenv("E2E_ALLOW_WRITES") != REQUIRED_SENTINEL,
    reason="Enable only in the disposable docker-compose.e2e.yml test runner",
)
GATEWAY = os.getenv("E2E_GATEWAY_URL", "http://api-gateway")
AUTH = os.getenv("E2E_AUTH_URL", "http://auth-service:8001")
TUITION = os.getenv("E2E_TUITION_URL", "http://tuition-service:8001")
MAILPIT = os.getenv("E2E_MAILPIT_URL", "http://mailpit:8025")
TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "")


def connect(kind):
    import psycopg2
    dsn = os.environ[f"E2E_{kind}_DSN"]
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    return conn


def eventually(predicate, timeout=35, interval=0.5):
    end = time.monotonic() + timeout
    last = None
    while time.monotonic() < end:
        try:
            result = predicate()
            if result:
                return result
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            last = exc
        time.sleep(interval)
    raise AssertionError(f"Condition not met within {timeout}s: {last}")


def messages_for(address):
    # Mailpit v1 message listing, only isolated container SMTP sink.
    response = httpx.get(f"{MAILPIT}/api/v1/messages", timeout=5)
    response.raise_for_status()
    return [m for m in response.json().get("messages", [])
            if any(a.get("Address", "").lower() == address.lower() for a in m.get("To", []))]


def otp_for(address):
    def find():
        for msg in messages_for(address):
            match = re.search(r"\[(\d{6})\]", msg.get("Subject", ""))
            if match:
                return match.group(1)
        return None
    return eventually(find)


@pytest.fixture
def records():
    assert TOKEN and len(TOKEN) > 8, "Internal test service token must be configured"
    tag = uuid.uuid4().hex[:11]
    # Always unique rows; never mutate or delete seeded demo records.
    uid1, uid2 = f"e2e-u1-{tag}", f"e2e-u2-{tag}"
    student = "8" + str(int(tag[:8], 16) % 10**9).zfill(9)
    email1, email2 = f"{uid1}@example.com", f"{uid2}@example.com"    
    username1, username2 = f"e2e1_{tag}", f"e2e2_{tag}"
    auth = connect("AUTH"); tuition = connect("TUITION"); payment = connect("PAYMENT")
    created_ids = []
    try:
        with auth.cursor() as cur:
            cur.execute("SELECT hashed_password FROM users WHERE username='sv001'")
            demo = cur.fetchone()
            assert demo, "Requires SEED_DEMO_DATA=true in disposable E2E stack"
            for uid, username, address in [(uid1, username1, email1), (uid2, username2, email2)]:
                cur.execute("INSERT INTO users(id,username,hashed_password,name,email,balance) VALUES (%s,%s,%s,%s,%s,%s)",
                            (uid,username,demo[0],"E2E Test User",address,Decimal("1000.00")))
        with tuition.cursor() as cur:
            cur.execute("INSERT INTO tuitions(student_code,student_name,tuition_fee,is_paid) VALUES (%s,%s,800,false)",
                        (student,"E2E Student"))
        fixture = {"users": [uid1,uid2], "usernames": [username1,username2], "emails": [email1,email2],
                   "student": student, "auth": auth, "tuition": tuition, "payment": payment,
                   "created_ids": created_ids}
        yield fixture
    finally:
        # Rows are not shared with real user data; guarantee cleanup even after assertion failures.
        # Clean outbox first to avoid FK conflicts; payment-worker may already have delivered receipt.
        try:
            with payment.cursor() as cur:
                cur.execute("SELECT id FROM transactions WHERE user_id IN (%s,%s)", (uid1,uid2))
                ids = [row[0] for row in cur.fetchall()]
                if ids:
                    cur.execute("DELETE FROM outbox_events WHERE aggregate_id = ANY(%s)", (ids,))
                    cur.execute("DELETE FROM transactions WHERE id = ANY(%s)", (ids,))
            with auth.cursor() as cur:
                cur.execute("DELETE FROM wallet_operations WHERE user_id IN (%s,%s)", (uid1,uid2))
                cur.execute("DELETE FROM users WHERE id IN (%s,%s)", (uid1,uid2))
            with tuition.cursor() as cur:
                cur.execute("DELETE FROM tuitions WHERE student_code=%s", (student,))
        finally:
            auth.close(); tuition.close(); payment.close()


def login(username):
    resp = httpx.post(f"{GATEWAY}/api/auth/login", json={"username":username,"password":"123456"}, timeout=15)
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['token']}"}


def test_gateway_blocks_internal_mutations():
    for endpoint in ("/api/auth/deduct", "/api/auth/refund", "/api/tuitions/123456/pay"):
        res = httpx.post(GATEWAY + endpoint, json={}, timeout=10)
        assert res.status_code == 404, (endpoint, res.text)


def test_parallel_debits_no_overdraft_and_idempotent(records):
    uid = records["users"][0]
    ids = [f"e2e-debit-{uuid.uuid4().hex[:20]}" for _ in range(2)]
    def debit(tid):
        return httpx.post(f"{AUTH}/api/auth/deduct", json={"user_id":uid,"amount":"800.00","transaction_id":tid},
                          headers={"X-Internal-Token":TOKEN},timeout=20)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(debit, ids))
    assert sorted([r.status_code for r in results]) == [200,400], [(r.status_code,r.text) for r in results]
    succeeded = ids[[r.status_code for r in results].index(200)]
    repeat = debit(succeeded)
    assert repeat.status_code == 200 and repeat.json()["already_applied"] is True
    with records["auth"].cursor() as cur:
        cur.execute("SELECT balance FROM users WHERE id=%s", (uid,))
        assert cur.fetchone()[0] == Decimal("200.00")
        cur.execute("SELECT count(*) FROM wallet_operations WHERE user_id=%s AND operation='DEBIT'", (uid,))
        assert cur.fetchone()[0] == 1


def test_parallel_tuition_payments_only_one_winner(records):
    ids = [f"e2e-pay-{uuid.uuid4().hex[:20]}" for _ in range(2)]
    def settle(tid):
        return httpx.post(f"{TUITION}/api/tuitions/{records['student']}/pay",
                          json={"transaction_id":tid},headers={"X-Internal-Token":TOKEN},timeout=20)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(settle, ids))
    assert sorted([r.status_code for r in results]) == [200,409], [(r.status_code,r.text) for r in results]
    winner = ids[[r.status_code for r in results].index(200)]
    same = settle(winner)
    assert same.status_code == 200 and same.json()["already_applied"] is True
    with records["tuition"].cursor() as cur:
        cur.execute("SELECT is_paid,paid_transaction_id FROM tuitions WHERE student_code=%s", (records["student"],))
        assert cur.fetchone() == (True,winner)


def test_real_otp_payment_history_and_receipt(records):
    h = login(records["usernames"][0]); email = records["emails"][0]
    assert httpx.get(f"{GATEWAY}/api/tuitions/{records['student']}",timeout=10).status_code == 200
    started = httpx.post(f"{GATEWAY}/api/payments/init",json={"mssv":records["student"]},headers=h,timeout=20)
    assert started.status_code == 201, started.text
    transaction = started.json()["transaction_id"]
    wrong = httpx.post(f"{GATEWAY}/api/payments/verify-otp",
                       json={"transaction_id":transaction,"otp":"000000"},headers=h,timeout=20)
    otp = otp_for(email)
    # The rare random coincidence of generated OTP being 000000 is already excluded by OTP generation.
    assert wrong.status_code == 400, wrong.text
    success = httpx.post(f"{GATEWAY}/api/payments/verify-otp",
                         json={"transaction_id":transaction,"otp":otp},headers=h,timeout=35)
    assert success.status_code in {200,503}, success.text
    def finished():
        r = httpx.get(f"{GATEWAY}/api/payments/status/{transaction}",headers=h,timeout=12)
        return r.json().get("transaction",{}).get("status") == "success"
    eventually(finished,timeout=45)
    again = httpx.post(f"{GATEWAY}/api/payments/verify-otp",
                       json={"transaction_id":transaction,"otp":otp},headers=h,timeout=20)
    assert again.status_code == 200
    history = httpx.get(f"{GATEWAY}/api/payments/history",headers=h,timeout=15)
    assert history.status_code == 200 and sum(t["id"]==transaction for t in history.json()["transactions"])==1
    user = httpx.get(f"{GATEWAY}/api/auth/me",headers=h,timeout=15)
    assert Decimal(str(user.json()["balance"])) == Decimal("200.00")
    tuition = httpx.get(f"{GATEWAY}/api/tuitions/{records['student']}",timeout=15)
    assert tuition.json()["is_paid"] is True
    with records["auth"].cursor() as cur:
        cur.execute("SELECT count(*) FROM wallet_operations WHERE user_id=%s AND operation='DEBIT'",(records["users"][0],))
        assert cur.fetchone()[0] == 1
    def has_receipt():
        return any(transaction in m.get("Subject", "") for m in messages_for(email))
    eventually(has_receipt,timeout=45)


def test_expired_otp_rejected_without_debit(records):
    h = login(records["usernames"][0]);
    response = httpx.post(f"{GATEWAY}/api/payments/init",json={"mssv":records["student"]},headers=h,timeout=20)
    assert response.status_code == 201, response.text
    transaction = response.json()["transaction_id"]
    otp = otp_for(records["emails"][0])
    with records["payment"].cursor() as cur:
        cur.execute("UPDATE transactions SET otp_expires_at=now() - interval '60 seconds' WHERE id=%s", (transaction,))
    reply = httpx.post(f"{GATEWAY}/api/payments/verify-otp",
                       json={"transaction_id":transaction,"otp":otp},headers=h,timeout=20)
    assert reply.status_code == 400, reply.text
    with records["auth"].cursor() as cur:
        cur.execute("SELECT balance FROM users WHERE id=%s",(records["users"][0],))
        assert cur.fetchone()[0] == Decimal("1000.00")


def test_two_accounts_race_same_tuition_full_saga(records):
    """Both payers pass OTP; only one settlement succeeds, loser gets compensation."""
    headers = [login(name) for name in records["usernames"]]
    ids = []
    for auth in headers:
        r = httpx.post(f"{GATEWAY}/api/payments/init", json={"mssv": records["student"]},
                       headers=auth, timeout=20)
        assert r.status_code == 201, r.text
        ids.append(r.json()["transaction_id"])
    otps = [otp_for(email) for email in records["emails"]]

    def verify(i):
        return httpx.post(f"{GATEWAY}/api/payments/verify-otp",
                          headers=headers[i], json={"transaction_id": ids[i], "otp": otps[i]}, timeout=40)

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(verify, (0, 1)))
    assert all(r.status_code in {200, 409, 503} for r in responses), [(r.status_code, r.text) for r in responses]

    def both_terminal():
        states = []
        for i in (0, 1):
            response = httpx.get(f"{GATEWAY}/api/payments/status/{ids[i]}", headers=headers[i], timeout=10)
            assert response.status_code == 200, response.text
            states.append(response.json()["transaction"]["status"])
        return states if sorted(states) == ["failed", "success"] else None

    states = eventually(both_terminal, timeout=90)
    winner = states.index("success")
    with records["tuition"].cursor() as cur:
        cur.execute("SELECT is_paid,paid_transaction_id FROM tuitions WHERE student_code=%s", (records["student"],))
        assert cur.fetchone() == (True, ids[winner])
    with records["auth"].cursor() as cur:
        cur.execute("SELECT id,balance FROM users WHERE id IN (%s,%s)", tuple(records["users"]))
        balances = dict(cur.fetchall())
        assert balances[records["users"][winner]] == Decimal("200.00")
        assert balances[records["users"][1-winner]] == Decimal("1000.00")
        cur.execute("SELECT operation,user_id FROM wallet_operations WHERE user_id IN (%s,%s)", tuple(records["users"]))
        operations = cur.fetchall()
        assert sum(op == "DEBIT" for op, _ in operations) in (1, 2)
        assert sum(op == "DEBIT" for op, _ in operations) - sum(op == "REFUND" for op, _ in operations) == 1
