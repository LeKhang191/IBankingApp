# Rubric-oriented demo checklist (run locally before claiming 10/10)

- [ ] PlantUML use-case, ERD, microservices architecture diagrams render and match code.
- [ ] `docker compose config --quiet`; `docker compose up -d --build`; all health checks green.
- [ ] Database roles isolated: auth_db, tuition_db, payment_db; unique/check constraints + no volume resets.
- [ ] Login (401 wrong password, 200 correct), balance and tuition lookup.
- [ ] OTP arrives by real configured email, invalid/expired/replayed OTP rejected. Never expose OTP in API response.
- [ ] Correct OTP: one debit, tuition paid, payment history and receipt in email.
- [ ] `pytest tests/unit -q` passes.
- [ ] Isolated real HTTP E2E suite passes, including concurrent debit, concurrent tuition settlement, two-user full Saga settlement/compensation and idempotency.
- [ ] In logs, request ID follows gateway -> payment -> auth/tuition/notification; worker has own ID for jobs.
- [ ] Explain Saga retries/compensation and at-least-once outbox/email semantics.
- [ ] Explain that correlated logs are not full distributed tracing; optional instrumentation if time.
- [ ] Document legacy DB migration steps and verified backup; don't use `down -v` on user data.
