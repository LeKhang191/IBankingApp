# iBanking: 3 one-click launchers (Windows)

**Prerequisite: Docker Desktop installed with Linux containers / WSL2 enabled.** No host installation of Node.js, Python, npm, pytest or PostgreSQL is needed. The first run requires Internet access to pull Docker images and download packages inside images/containers. Docker may need to be started and authorized by Windows.

Double-click exactly one of these files **in the project root**:

| File | Purpose |
| --- | --- |
| `ONECLICK-1-START.bat` | Check Docker; generate `.env` with random secrets only if missing; build and start the app; check HTTP; open login page and demo Mailpit inbox. |
| `ONECLICK-2-AUTOMATION.bat` | Start an **isolated** Docker test stack; run Saga/Outbox workflow smoke and PostgreSQL concurrency tests. |
| `ONECLICK-3-E2E.bat` | Start the isolated stack; run HTTP E2E test suite (OTP, payment, history, Saga, race conditions, Mailpit receipt). |

They call the shared helper `scripts/oneclick.ps1`. All other app source files and existing scripts are retained. The three `.bat` files are the only entrypoints you need to double-click.

## App URLs

- App: http://localhost:5173/dang-nhap
- Gateway: http://localhost:8080/health
- Inbox for demo OTP / receipt: http://localhost:18026

Start mode uses `docker-compose.oneclick.yml` as a local-only override. It routes the notification service to Mailpit **even if an existing `.env` has Gmail SMTP settings**. This does not alter `.env`. If real email is required, launch with the normal `docker compose up -d --build` instead, after configuring Gmail SMTP.

On a **new** machine without `.env`, the helper creates a private `.env` containing random DB passwords and secrets, and demo data is enabled. On a machine with `.env`, it does not modify it. Copy your original `.env` before replacing a source directory if you want to keep the existing database credentials. Never share or commit `.env`.

## Safety and testing

Automation and E2E run through `docker-compose.e2e.yml`, Compose project `ibanking-disposable-e2e` (different database volume and ports from the main app). Tests may insert/delete **disposable test rows**. Neither launcher deletes volumes, calls `down -v`, or intentionally modifies the normal application's DB. Still, keep important data backed up and do not modify the E2E project name to match the main project.

E2E uses Mailpit http://localhost:18025 and Gateway http://localhost:18080. The automation concurrency test uses disposable test tables on the **E2E payment database**, not your normal DB. It simulates locking/idempotency invariants. The HTTP E2E tests exercise actual services.

Successful launchers print `[PASS]` at the end. On failure, the window remains open with an error. Common diagnostic commands, from project root:

```powershell
docker compose ps
docker compose logs --tail=100
# For automation / E2E:
docker compose -f docker-compose.e2e.yml ps -a
docker compose -f docker-compose.e2e.yml logs --tail=100
```

## Limitations

- Docker Desktop **must already be installed**, per the requested scenario. The launcher can try starting it, but cannot silently install Docker, enable Windows virtualization or approve UAC dialogs.
- The app assumes host ports **5173, 8080, 5432, 18026** are free; E2E additionally requires **15173, 18080, 55432, 18025**. If another program occupies them, Docker prints a port conflict.
- The generated `.env` is for an empty demo installation. Existing PostgreSQL data volumes retain their initialized DB passwords; a newly generated `.env` cannot reset them.
- Runtime on Windows/Docker Desktop must be validated on the destination machine. This package has been structurally checked, not Docker-run in this sandbox.
