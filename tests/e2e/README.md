# Real HTTP integration/E2E tests — isolated environment

**DANGER:** these tests create and remove database rows. Run against the dedicated `ibanking-disposable-e2e` Compose project ONLY. Never use production `.env` data/volumes or set `E2E_ALLOW_WRITES` for the normal application. The separate stack uses a Mailpit SMTP sink and a distinct named Postgres volume.

## Prerequisites
Docker Compose, local `.env` with valid database passwords/JWT/internal token/OTP pepper. Use a **disposable test-specific `.env`**, never the deployed project secrets.

```bash
# From project root, test-specific .env present:
docker compose -f docker-compose.e2e.yml up -d --build postgres db-bootstrap auth-service tuition-service notification-service payment-service payment-worker api-gateway mailpit
docker compose -f docker-compose.e2e.yml run --rm e2e-tests
docker compose -f docker-compose.e2e.yml ps
```

Mailpit inbox: http://localhost:18025; Gateway: http://localhost:18080.

Expected assertions: HTTP gateway blocks internal mutations; 2 parallel debit calls cause exactly one success, one 400, one wallet debit; 2 tuition settlement calls cause exactly one success, one 409; two users concurrently confirming OTP for the same tuition triggers one successful Saga and compensation of the losing debit; OTP email/verification -> one debit -> tuition paid -> history -> receipt email; expired OTP rejects without debit.

If all work and **you are certain this is only the disposable E2E stack**, clean its separate volume with:

```bash
docker compose -f docker-compose.e2e.yml down -v
```

**Do not use `down -v` without `-f docker-compose.e2e.yml`.** Existing production data is not touched by the runner but incorrect Docker project/volumes can still be dangerous. A failed E2E test must be diagnosed with `docker compose -f docker-compose.e2e.yml logs --tail=120`.

Caveat: no E2E checks have been executed in a Docker environment by this delivery. The tests must pass on your computer to establish runtime correctness.

## One-command PowerShell wrapper

From the repository root, run `.\tests\e2e\run-e2e.ps1 -Build`. The wrapper starts only the isolated E2E stack and runs the `e2e-tests` service. It does **not** remove volumes or affect the ordinary Compose project.
