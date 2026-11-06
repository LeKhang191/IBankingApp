# iBanking - Tuition Payment Microservices

This project demonstrates a student tuition payment workflow using a React frontend and four FastAPI services: Auth, Tuition, Payment, and Notification.

## Architecture and diagrams

See `docs/` for the Use Case, ERD, and Microservices Architecture diagram source files. The current Phase 1 patch still uses one PostgreSQL database shared by the service containers; separate database ownership is planned as Phase 2.

## Run locally with Docker Compose

1. Copy `.env.example` to `.env` and replace every placeholder with a unique secret and valid SMTP credentials.
2. Run `docker compose up --build -d`.
3. Open the frontend at `http://localhost:5173`.
4. API documentation is available at `http://localhost:8000/docs`, `http://localhost:8002/docs`, and `http://localhost:8003/docs`.

For an existing database, read `APPLY_PHASE1.md` and run the migration in `docs/phase1_migration.sql` after backing up PostgreSQL.

## Demo accounts

The Auth Service seeds demo users only when the users table is empty. Check the configured seed credentials in `backend/auth-service/app/crud.py` before presenting. Change them before any public deployment.

## Important security note

Do not commit `.env`, SMTP app passwords, JWT secrets, or internal service tokens. If any credential has been committed or shared, rotate it. The supplied ZIP contained `.env` files; treat their secrets as exposed.

## Project quality status

This repository is a coursework/demo system, not a production banking system. Read `APPLY_PHASE1.md` for the changes in Phase 1 and the remaining engineering work needed for stronger transaction recovery, separate data ownership, automated concurrency testing, API Gateway, and observability.
