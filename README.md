# iBanking — Tuition Payment Microservices

A coursework project for student tuition payment using a React frontend and four FastAPI services: Auth, Tuition, Payment, and Notification.

## Phase 2 architecture

The data-owning services now have separate PostgreSQL databases and dedicated login roles:

| Service | Database | Owner |
|---|---|---|
| Auth | `auth_db` | `auth_user` |
| Tuition | `tuition_db` | `tuition_user` |
| Payment | `payment_db` | `payment_user` |
| Notification | No database | N/A |

The services share one PostgreSQL server/container, not one application database. Each application role is granted connection only to its own database. Service-to-service business operations use HTTP APIs. See `docs/microservices-architecture.puml`.

## Run

1. Copy `.env.example` to `.env` only for a new install. For an existing Phase 1 install, keep the current root `.env` and add the Phase 2 database variables from `APPLY_PHASE2.md`.
2. Ensure the root `.env` contains distinct `AUTH_DB_PASSWORD`, `TUITION_DB_PASSWORD`, and `PAYMENT_DB_PASSWORD` values.
3. Validate and start:

   ```powershell
   docker compose config --quiet
   docker compose up --build -d
   docker compose ps
   ```

4. Open `http://localhost:5173`. OpenAPI docs: `http://localhost:8000/docs`, `http://localhost:8002/docs`, and `http://localhost:8003/docs`.

For an existing Phase 1 database, follow **all** backup, schema migration, and data migration steps in `APPLY_PHASE2.md` before using the Phase 2 databases for demo.

## Diagrams

- `docs/use-case.puml`
- `docs/erd.puml`
- `docs/microservices-architecture.puml`

## Tests

- `scripts/test-db-isolation.sh`: verifies service roles can connect to their own database and cannot connect to the other service databases.
- `tests/concurrency_smoke.py`: API-level concurrency smoke test for concurrent wallet debits and tuition settlement. Use a disposable tuition row.

## Security

Do not commit `.env`, SMTP app passwords, JWT signing secrets, internal service tokens, or database passwords. If a credential has been exposed, rotate it. This is an academic demonstration system, not a production banking platform.

## Current engineering scope

Phase 2 establishes database-per-service ownership and a legacy data migration path. Alembic migrations, durable Saga recovery, transactional outbox workers, API Gateway, structured logs/correlation IDs, and distributed tracing remain separate implementation tasks.
