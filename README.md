> **Windows one-click:** Double-click `ONECLICK-1-START.bat` to start the demo, `ONECLICK-2-AUTOMATION.bat` to run workflow + concurrency automation, or `ONECLICK-3-E2E.bat` for HTTP E2E tests. See [ONECLICK-README.md](ONECLICK-README.md).

# iBanking — Microservices tuition payment

FastAPI + React/Vite + PostgreSQL. Four business services (`auth`, `tuition`, `payment`, `notification`) plus Nginx API Gateway and payment Saga/outbox worker. Auth, tuition, and payment each own a **separate database and role**. Notification sends email but does not own a database.

## Quick start (fresh install)

1. `cp .env.example .env` (Windows: `copy .env.example .env`) and replace **all** sample secrets and SMTP details. Never commit `.env`.
2. `docker compose up -d --build`
3. Open `http://localhost:5173`, or `http://localhost:8080/health` for the API Gateway.
4. Use `docker compose ps` and `docker compose logs --tail=100 payment-worker` for diagnostics.

The frontend uses **real API endpoints** through the gateway:
- `/api/auth/*` -> Auth Service
- `/api/tuitions/*` -> Tuition Service
- `/api/payments/*` -> Payment Service

Internal debit/refund and tuition settlement endpoints are blocked at the gateway; they are available only on the Docker service network with an internal token. Business service ports are **internal-only** (`expose`) by default; only the API Gateway is published.

## Database

See [database/README.md](database/README.md) and [APPLY_PHASE3.md](APPLY_PHASE3.md) before upgrading an existing database. **Do not reset volumes**. Schema owners: `backend/*/app/models.py`. SQL migrations: `database/migrations/<service>/`. `docs/erd.puml` is a conceptual ERD.

## Workflow

Login -> tuition lookup -> start payment -> email OTP -> verify -> idempotent debit -> tuition settlement -> outbox/receipt -> status and history. Saga worker retries temporary failures and compensates confirmed tuition conflicts. Email receipt is at-least-once; SMTP cannot guarantee exactly once.

## Logging and observability

The gateway emits structured access lines with a request ID, and each API service writes request ID, method, path, status, latency and unhandled errors to Docker logs. Payment propagates the ID to downstream calls. This is **correlation logging, not distributed tracing** (no Jaeger/Zipkin spans).

## Tests and limitations

Run offline tests with ` .\tests\automation\test-workflow.ps1` after installing backend development dependencies. Run `test-workflow.bat` for environment smoke checks on Windows (internal-only services are checked via `docker compose exec`). See `tests/README.md` for automation and opt-in PostgreSQL concurrency tests. A configured PostgreSQL + SMTP environment is necessary to verify full workflow; successful static/unit checks do not prove a deployed system works.

## Diagrams

`docs/use-case.puml`, `docs/erd.puml`, `docs/microservices-architecture.puml` (PlantUML). The source folder structure is documented in `docs/PROJECT_STRUCTURE.md`.

## Isolated real HTTP / OTP E2E tests
See `tests/e2e/README.md`: use the dedicated `docker-compose.e2e.yml` stack (separate PostgreSQL volume, Mailpit email sink) and run the opt-in suite against **only that** stack. No production SMTP messages are sent.

## Test layout (automation vs end-to-end)

- `tests/automation/test-workflow.ps1`: payment Saga/Outbox smoke test.
- `tests/automation/test-concurrency.ps1`: optional disposable PostgreSQL concurrency test.
- `tests/automation/`: workflow/concurrency tests only.
- `tests/e2e/`: isolated full HTTP workflow, OTP, Mailpit and Saga tests.

From PowerShell: `.\tests\automation\test-workflow.ps1` or `.\tests\e2e\run-e2e.ps1 -Build`. See `tests/README.md`. The `test-workflow.bat` shortcut remains compatible.
