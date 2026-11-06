# Database ownership and migrations

Three **separate PostgreSQL databases and credentials**, provisioned by `bootstrap/`:

| Owner | Database | Main tables | Schema source |
|---|---|---|---|
| Auth Service | `auth_db` | `users`, `wallet_operations` | `backend/auth-service/app/models.py` |
| Tuition Service | `tuition_db` | `tuitions` | `backend/tuition-service/app/models.py` |
| Payment Service | `payment_db` | `transactions`, `outbox_events` | `backend/payment-service/app/models.py` |

Notification is stateless; payment service owns the durable outbox.

## Fresh install
`docker compose up -d --build` creates the roles/databases via `db-bootstrap`; each service creates its own tables via SQLAlchemy on startup. Fresh schemas already include checks and unique constraints. Demo seed runs only when the corresponding tables are empty and `SEED_DEMO_DATA=true`.

## Existing database / migrations
**Back up first**. `Base.metadata.create_all` does NOT alter existing tables. Apply only migrations needed for an existing deployment. For a Phase 2 -> Phase 3 upgrade run `payment/001_saga_outbox.sql` against `payment_db` **before** starting the new payment API or worker; then apply `payment/002_constraints.sql`. Apply `auth/001_constraints.sql` to `auth_db` and `tuition/001_constraints.sql` to `tuition_db`. Do not run legacy migration against these service databases.

Example commands (after `docker compose up -d postgres db-bootstrap` and before app start):

```bash
docker compose exec -T postgres psql -U postgres -d auth_db < database/migrations/auth/001_constraints.sql
docker compose exec -T postgres psql -U postgres -d tuition_db < database/migrations/tuition/001_constraints.sql
docker compose exec -T postgres psql -U postgres -d payment_db < database/migrations/payment/001_saga_outbox.sql
docker compose exec -T postgres psql -U postgres -d payment_db < database/migrations/payment/002_constraints.sql
```

For already running Phase 3 installations, skip `001_saga_outbox.sql` if already applied. Check constraints require that historical records satisfy them. **Never run `docker compose down -v` to apply a migration.** Scripts under `legacy/` are for the original single-DB schema and are NOT used for fresh installation.
