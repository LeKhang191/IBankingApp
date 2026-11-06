# Upgrade to Phase 3 safely

1. Set strong secrets by copying `.env.example` to `.env` ONLY on a new deployment. Keep an existing `.env` unchanged.
2. Back up `auth_db`, `tuition_db`, and `payment_db` before any migration.
3. Start PostgreSQL/bootstrap: `docker compose up -d postgres db-bootstrap` and wait for bootstrap success.
4. On an existing Phase 2 database, run `database/migrations/payment/001_saga_outbox.sql` against `payment_db`. Fresh installations already get these columns/tables from models.
5. Run the relevant idempotent constraints migrations as described in `database/README.md` for existing databases.
6. Start all services: `docker compose up -d --build`.
7. Visit `http://localhost:5173`, gateway health `http://localhost:8080/health`, and inspect `docker compose logs -f payment-worker`.

Never delete the PostgreSQL volume during an upgrade. SMTP needs real credentials to deliver OTP and receipt; do not log or return OTP to browser. Unit tests are offline; live concurrency integration tests require isolated throwaway data.
