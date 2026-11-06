# Testing strategy

1. **Offline unit/schema tests:** `python -m pytest tests/unit -q` requires `pytest` and `sqlalchemy`; validates independent service-owned schema constraints and gateway routes. No database changes.
2. **Real PostgreSQL concurrency test (opt in):** set `TEST_DATABASE_URL` to a **disposable PostgreSQL test database**, then `python -m pytest tests/integration -q`. Tests use separate disposable tables, verify two concurrent debits cannot overdraw and two tuition settlements cannot both win. This validates locking strategy, **not** the end-to-end HTTP Saga.
3. **Existing Saga/outbox smoke (with Docker):** `docker compose exec payment-service python -m app.tests.phase3_saga_smoke`. HTTP calls to other services are mocked; it writes and cleans up test transactions in payment_db.
4. **Windows deployment smoke:** `test-workflow.bat` checks Compose services, health endpoints and DB state.
5. **Manual E2E:** use a disposable demo account + SMTP sandbox mailbox to verify login -> tuition lookup -> OTP -> payment -> balance, paid status, history and email. Never run destructive demos against production.

**Important:** do not claim automated coverage proves actual concurrency across microservices. Full concurrency / failure-injection E2E tests and automated mail delivery checks are additional work before a genuine 10/10-level verification.
