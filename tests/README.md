# iBanking Windows workflow tests

These tests are non-destructive. They do not delete Docker volumes, reset balances, or create a real payment.

## Run on Windows

1. Copy `test-workflow.bat` to the project root (same level as `docker-compose.yml`).
2. Copy the `scripts` and `tests` folders into the project root. If `tests` already exists, merge the folders; do not delete existing tests.
3. Start the stack first:

   ```powershell
   docker compose up -d --build
   ```

4. Run by double-clicking `test-workflow.bat`, or from PowerShell:

   ```powershell
   .\test-workflow.bat
   ```

   Or run directly:

   ```powershell
   .\scripts\test-workflow.ps1
   ```

## Optional switches

- `.	est-workflow.bat -SkipSmokeTest` checks Docker, services, databases and Phase 3 tables, but skips the mocked Saga/Outbox test.
- `.	est-workflow.bat -ShowLogs` runs all checks and prints recent Payment Service/Worker logs.

## What is tested

- Docker Compose configuration and container availability.
- Auth, Tuition and Payment HTTP health endpoints.
- Notification Service health from inside its container.
- Payment Worker container availability.
- Presence of `auth_db`, `tuition_db`, and `payment_db`.
- Presence of `transactions` and `outbox_events` in `payment_db`.
- Existing `app.tests.phase3_saga_smoke` test: successful Saga + durable outbox event, failed outbox delivery retry, and compensation on a definitive tuition conflict. Auth/Tuition HTTP calls are mocked for this test; it does not perform a real debit or tuition payment.

## Real business workflow (manual)

The script cannot safely enter an OTP received in a private mailbox or operate the browser UI. After automated checks pass, manually test:

1. Open `http://localhost:5173`.
2. Sign in with a demo account that exists in the fresh database.
3. Look up an unpaid student record.
4. Start payment and receive OTP at the configured email.
5. Enter OTP and confirm payment.
6. Verify transaction status, wallet balance, tuition status, transaction history, and receipt email.

Do not use a real account or real balance for failure-injection tests. Use disposable demo data.
