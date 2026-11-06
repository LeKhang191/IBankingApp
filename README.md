# iBanking — Phase 3 Patch

This patch adds a recoverable payment Saga and a transactional outbox for receipt email delivery on top of the Phase 2 database-per-service architecture.

## Main additions

- Saga progress tracking in `payment_db`.
- Safe retry of idempotent debit, tuition settlement, and refund operations.
- A separate `payment-worker` container for Saga recovery.
- Transactional outbox: payment success and receipt-event creation commit together.
- Outbox retry with exponential backoff.
- Owner-protected payment status API and OTP page polling.

## Apply

Follow [`APPLY_PHASE3.md`](APPLY_PHASE3.md) from the project root. Back up `payment_db`, apply `docs/phase3_payment_migration.sql`, then build and start `payment-service`, `payment-worker`, and `frontend`.

Do not overwrite the real `.env` with `.env.example`, and do not run `docker compose down -v`.

## Important delivery guarantee

The outbox provides at-least-once delivery. A receipt is durably queued with payment success and retried if Notification Service/SMTP is temporarily unavailable. SMTP cannot provide exactly-once delivery; a duplicate receipt is possible if the SMTP provider accepts a message but its acknowledgement is lost.
