# iBanking - Phase 1 patch

This patch fixes several correctness/security defects in the supplied project. It is **not** a complete 10/10 implementation. It is the first implementation pass for payment consistency, idempotency, OTP handling, service-to-service authentication, and frontend API consistency.

## Files replaced/added

- `backend/auth-service/app/models.py`
- `backend/auth-service/app/routers/auth.py`
- `backend/tuition-service/app/models.py`
- `backend/tuition-service/app/schemas.py`
- `backend/tuition-service/app/routers/tuition.py`
- `backend/tuition-service/app/main.py`
- `backend/payment-service/app/models.py`
- `backend/payment-service/app/main.py`
- `backend/notification-service/app/main.py`
- `frontend/src/services/paymentService.js`
- `frontend/src/services/tuitionService.js`
- `frontend/src/pages/PaymentConfirmPage.jsx`
- `frontend/src/pages/OtpPage.jsx`
- `docker-compose.yml`
- `.env.example`, `.gitignore`, `docs/`

## Apply it

1. Stop the current containers, but **do not** remove the database volume:

   ```bash
   docker compose down
   ```

2. Back up PostgreSQL before applying schema changes:

   ```bash
   docker compose up -d postgres
   docker compose exec -T postgres pg_dump -U postgres -d ibanking > ibanking-before-phase1.sql
   ```

   If your existing PostgreSQL user/database names differ, adjust the `pg_dump` command.

3. Copy the patch contents over the project root. Allow the listed files to be overwritten. Do not copy a `.env` file from anywhere; the patch intentionally contains no secrets.

4. Update the **existing root `.env`** with the variables in `.env.example`. The old Compose file hard-coded the PostgreSQL login as `postgres`; the new Compose file keeps that username but reads its password from `.env`. If this is an existing `pgdata` volume, change the PostgreSQL role password inside the running container before starting the app services:

   ```bash
   docker compose exec postgres psql -U postgres -d ibanking
   ```

   Then execute `ALTER USER postgres WITH PASSWORD 'YOUR_NEW_POSTGRES_PASSWORD';` in the SQL prompt and exit with `\q`. Use the same value for `POSTGRES_PASSWORD` in `.env`.

   Generate fresh application secrets, for example:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

   Generate separate values for `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `INTERNAL_SERVICE_TOKEN`, and `OTP_PEPPER`. Do not reuse the same value. Keep the PostgreSQL password URL-safe (the command above is suitable).

5. For an **existing database** created by the old project, run this migration before starting the new backend containers:

   ```bash
   docker compose exec -T postgres psql -U postgres -d ibanking < docs/phase1_migration.sql
   ```

   For a brand-new empty database, skip this SQL migration; the services create the new tables/columns on startup.

6. Rebuild and start:

   ```bash
   docker compose up --build -d
   docker compose ps
   docker compose logs -f auth-service tuition-service payment-service notification-service
   ```

7. Check service health:

   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8002/health
   curl http://localhost:8003/health
   ```

## Behavior changed

- Wallet debit/refund requires a transaction ID and is idempotent per transaction.
- A duplicate debit does not deduct the balance a second time.
- Tuition settlement locks the tuition row and records the winning transaction ID; a different transaction cannot pay the same tuition again.
- `paid_at` now exists in the Tuition model (the old endpoint attempted to write a field that did not exist).
- OTP is generated with `secrets`, persisted as an HMAC digest, expires, and has a maximum attempt count.
- Resend OTP reuses the same transaction instead of creating another transaction.
- Payment verify/history check transaction ownership.
- Notification and tuition settlement endpoints require `INTERNAL_SERVICE_TOKEN`.
- Frontend payment calls use one `paymentService` instead of hard-coded calls scattered through pages.
- Demo tuition data is no longer reset to unpaid whenever Tuition Service restarts.

## Manual acceptance tests

1. Log in as a user with enough balance, search an unpaid student, request OTP, pay, and check the updated balance/history/email.
2. Submit the same OTP/transaction twice. The balance must only be reduced once; the second request should report the completed transaction or a processing response.
3. Attempt to use one user's transaction ID while logged in as another user. The API must return 404.
4. Open two sessions with different users and attempt to pay the same MSSV. At most one transaction may mark the tuition paid. The losing transaction must be refunded.
5. Try an incorrect OTP five times; the transaction must lock.
6. Try to call Tuition `POST /api/tuitions/{mssv}/pay` or Notification endpoints without `X-Internal-Token`; they must reject the request.
7. Restart Tuition Service after a payment. The tuition must remain paid.

## Known remaining work before aiming at 10/10

- Phase 1 still uses the same PostgreSQL database for the three data-owning services. Split into `auth_db`, `tuition_db`, and `payment_db` with explicit service ownership and migrations.
- Add a durable Saga recovery mechanism and transactional outbox for receipt/OTP delivery. A process crash between remote service calls can leave a transaction in `processing` or `compensation_required`; the idempotent operations make safe retry possible, but a worker/reconciliation flow is still needed.
- Add `Idempotency-Key` support for payment initialization.
- Replace `BackgroundTasks` email delivery with an outbox/worker and retry/dead-letter handling.
- Add automated unit, integration, end-to-end, and PostgreSQL concurrency tests. In particular, test parallel debits on one account and parallel settlement requests on one tuition row.
- Add API Gateway/reverse proxy, structured logging, correlation IDs, and tracing.
- Render and verify the Use Case, ERD, and Microservices diagrams; publish OpenAPI docs and a full README/demo script.
- Add database migrations (Alembic) rather than relying on `create_all` for production schema changes.
