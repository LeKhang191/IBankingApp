# iBanking Phase 2 — Separate database ownership

This patch changes the three data-owning services from one shared PostgreSQL database to three separately-owned databases and login roles:

| Service | Database | Login role | Tables owned |
|---|---|---|---|
| Auth Service | `auth_db` | `auth_user` | `users`, `wallet_operations` |
| Tuition Service | `tuition_db` | `tuition_user` | `tuitions` |
| Payment Service | `payment_db` | `payment_user` | `transactions` |
| Notification Service | No database | N/A | Sends email through SMTP |

The services still use one PostgreSQL server/container, but each application role can connect only to its own database. Cross-service data access remains through HTTP APIs.

## Important: preserve the current data

Do not run `docker compose down -v`. Do not delete the `pgdata` volume. The legacy Phase 1 database (`ibanking`) is retained as the migration source.

The root `.env` is intentionally not included in this patch. Add the Phase 2 variables shown in `.env.example` to the existing root `.env`. The Phase 1 Compose file in this repository initialized PostgreSQL with superuser `postgres` and database `ibanking` (it hard-coded those values even if `.env` contained different `POSTGRES_USER` / `POSTGRES_DB` values). Phase 2 deliberately keeps that same PostgreSQL superuser and legacy DB name. Keep the existing `POSTGRES_PASSWORD` value that currently lets the Phase 1 services connect. Do not rotate the PostgreSQL superuser password during this database split.

Generate three different URL-safe passwords for `AUTH_DB_PASSWORD`, `TUITION_DB_PASSWORD`, and `PAYMENT_DB_PASSWORD`. A PowerShell command to generate each value is:

```powershell
[Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```

Use a fresh result for each variable. Keep the DB passwords hexadecimal so they are safe inside the constructed PostgreSQL connection URLs.

## Apply on Windows PowerShell

Run all commands from the project root (the folder containing `docker-compose.yml`).

### 1. Back up the legacy database

```powershell
docker compose exec -T postgres sh -lc 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/ibanking-before-phase2.dump'
docker compose cp postgres:/tmp/ibanking-before-phase2.dump .\ibanking-before-phase2.dump
```

Confirm `ibanking-before-phase2.dump` exists before continuing.

### 2. Stop application containers but keep PostgreSQL running

```powershell
docker compose stop frontend auth-service tuition-service payment-service notification-service
```

### 3. Ensure the Phase 1 schema migration has been applied

The migration is idempotent and adds Phase 1 fields expected by the current code. Run it against the legacy `ibanking` database:

```powershell
Get-Content .\docs\phase1_migration.sql -Raw | docker compose exec -T postgres psql -U postgres -d ibanking -v ON_ERROR_STOP=1
```

If your initialized PostgreSQL superuser is not named `postgres`, replace that username with the value of `POSTGRES_USER` in `.env`.

### 4. Add Phase 2 variables to the existing root `.env`

Add these values (replace all three password placeholders with different random hexadecimal strings):

```env
AUTH_DB_NAME=auth_db
AUTH_DB_USER=auth_user
AUTH_DB_PASSWORD=PASTE_UNIQUE_64_HEX_CHARACTERS

TUITION_DB_NAME=tuition_db
TUITION_DB_USER=tuition_user
TUITION_DB_PASSWORD=PASTE_DIFFERENT_64_HEX_CHARACTERS

PAYMENT_DB_NAME=payment_db
PAYMENT_DB_USER=payment_user
PAYMENT_DB_PASSWORD=PASTE_ANOTHER_64_HEX_CHARACTERS

SEED_DEMO_DATA=false
```

Keep the other Phase 1 values in `.env`: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `JWT_SECRET_KEY`, `INTERNAL_SERVICE_TOKEN`, `OTP_PEPPER`, SMTP settings, CORS and Vite URLs.

### 5. Validate Compose and start the Phase 2 services

```powershell
docker compose config --quiet
docker compose up --build -d
```

Wait until `auth-service`, `tuition-service`, `payment-service`, and `notification-service` are healthy:

```powershell
docker compose ps
```

The three target databases are created by `db-bootstrap`. The services create their own tables on startup. Demo seeding is disabled temporarily so it cannot collide with imported records.

### 6. Migrate the existing Phase 1 data

```powershell
docker compose exec -T postgres sh /scripts/migrate-phase2-data.sh
```

This copies:

- `users` and `wallet_operations` from `ibanking` to `auth_db`;
- `tuitions` from `ibanking` to `tuition_db`;
- `transactions` from `ibanking` to `payment_db`.

The legacy `otp` plaintext column is deliberately not copied. Only columns represented by the current Payment model are imported. Legacy transactions without an OTP hash receive a dummy digest; Phase 1 migration has expired those pending legacy records.

The migration truncates the target service tables before importing. Run it only once for the initial migration, or intentionally when replacing all target data from the legacy database.

### 7. Re-enable demo seeding

Change this in `.env`:

```env
SEED_DEMO_DATA=true
```

Then recreate Auth and Tuition so the updated environment is loaded:

```powershell
docker compose up -d --force-recreate auth-service tuition-service
```

Existing imported data is preserved; the seed functions insert demo records only when their respective tables are empty.

### 8. Verify database isolation

```powershell
docker compose run --rm --no-deps db-bootstrap sh /scripts/test-db-isolation.sh
```

Expected output includes:

```text
PASS: auth_user connects to owned database auth_db
PASS: tuition_user connects to owned database tuition_db
PASS: payment_user connects to owned database payment_db
PASS: auth_user cannot connect to non-owned database tuition_db
PASS: auth_user cannot connect to non-owned database payment_db
...
PASS: database ownership isolation checks completed.
```

### 9. Verify ownership and application health

```powershell
docker compose exec postgres psql -U postgres -d postgres -c "SELECT datname, pg_get_userbyid(datdba) AS owner FROM pg_database WHERE datname IN ('auth_db','tuition_db','payment_db') ORDER BY datname;"

docker compose exec postgres psql -U postgres -d auth_db -c "SELECT tablename, tableowner FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"
docker compose exec postgres psql -U postgres -d tuition_db -c "SELECT tablename, tableowner FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"
docker compose exec postgres psql -U postgres -d payment_db -c "SELECT tablename, tableowner FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"

Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8002/health
Invoke-RestMethod http://localhost:8003/health
```

Expected owners: `auth_user`, `tuition_user`, and `payment_user` respectively.

### 10. Re-run the payment and concurrency flows

Use the same UI flow as Phase 1:

1. Log in.
2. Look up an unpaid student.
3. Initialize a payment.
4. Receive OTP by email.
5. Verify OTP.
6. Check the updated wallet balance, tuition status, transaction history, and receipt email.

Then run the Phase 1 API concurrency smoke test using a disposable tuition record:

```powershell
python -m pip install -r tests\requirements.txt
$env:TEST_USERNAME = "sv001"
$env:TEST_PASSWORD = "123456"
$env:TEST_TUITION_MSSV = "52999999"
$line = Get-Content .env | Where-Object { $_ -match '^INTERNAL_SERVICE_TOKEN=' } | Select-Object -First 1
$env:INTERNAL_SERVICE_TOKEN = $line.Substring('INTERNAL_SERVICE_TOKEN='.Length)
python tests\concurrency_smoke.py
```

## Troubleshooting

- **`password authentication failed`**: check that the three DB passwords in `.env` match the values in the compose environment. The `db-bootstrap` service resets the application roles' passwords each time it runs.
- **`relation ... does not exist` during data import**: wait for all three backend containers to start and become healthy so SQLAlchemy has created their target tables; then rerun the migration script.
- **`column ... does not exist` in the legacy database**: apply `docs/phase1_migration.sql` to the legacy `ibanking` DB, then rerun the data migration.
- **Cannot connect to database**: verify `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` still match the existing PostgreSQL volume. These initialization variables do not automatically reconfigure an existing volume.
- **Demo account not found**: make sure data migration copied users. Demo seeding runs only if the Auth users table is empty.

## Phase 2 scope and remaining work

This phase implements database-per-service ownership and an explicit data migration path. It does not yet introduce Alembic, a distributed Saga recovery worker, an outbox worker, an API Gateway, or OpenTelemetry. `create_all()` is still used to create target schemas for this coursework stage; schema evolution should move to Alembic in a later phase.
