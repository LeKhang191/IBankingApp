# Phase 3 migration — **existing data**

1. Take a verified `pg_dump` backup of **each** database. Keep your current `.env` (never commit it). Do not run `docker compose down -v`.
2. Stop `payment-service` and `payment-worker`. If upgrading from pre-Saga, apply `database/migrations/payment/001_saga_outbox.sql` to `payment_db`, then `002_constraints.sql`. Apply the auth/tuition constraint files if not already installed. See `database/README.md`.
3. Before applying `003_active_payment_unique.sql`, find conflicts:

```sql
SELECT user_id, mssv, count(*) FROM transactions
WHERE status IN ('pending','processing','compensation_required')
GROUP BY user_id, mssv HAVING count(*) > 1;
```

Resolve these conflicts by reconciling the real payment state; **do not delete or mark successful records failed blindly**. When the query returns zero rows, run:

```bash
docker compose exec -T postgres psql -U postgres -d payment_db < database/migrations/payment/003_active_payment_unique.sql
```

4. Rebuild/start services with `docker compose up -d --build`, inspect `docker compose ps` and worker logs. Verify `/health`, an end-to-end payment, and the history.
5. For disposable integration tests, use `docker-compose.e2e.yml` and `tests/e2e/README.md`; **never run those tests on an existing pgdata volume**.
