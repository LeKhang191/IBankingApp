# Project folder structure (source)

```text
IBankingApp-microservice/
├── .env.example
├── docker-compose.yml
├── docker-compose.e2e.yml           # Isolated real HTTP tests + Mailpit
├── README.md
├── APPLY_PHASE3.md
├── gateway/
│   └── nginx.conf                   # Browser API routing and internal endpoint blocking
├── database/
│   ├── README.md                    # DB ownership and migration procedure
│   ├── bootstrap/
│   │   ├── bootstrap-databases.sh   # Create separate databases and roles
│   │   └── bootstrap-databases.sql
│   ├── migrations/
│   │   ├── auth/001_constraints.sql
│   │   ├── tuition/001_constraints.sql
│   │   └── payment/
│   │       ├── 001_saga_outbox.sql
│   │       ├── 002_constraints.sql
│   │       └── 003_active_payment_unique.sql
│   └── legacy/phase1_monolith_migration.sql
├── backend/
│   ├── auth-service/app/            # User, wallet ledger, token & guarded debit/refund
│   ├── tuition-service/app/         # Tuition ownership and single-settlement lock
│   ├── payment-service/app/         # OTP, Saga, outbox, worker, history
│   └── notification-service/app/    # Email OTP and receipt
├── frontend/
│   └── src/
│       ├── components/
│       ├── context/
│       ├── pages/
│       ├── services/                 # Auth/payment/tuition, real axios client
│       └── utils/format.js
├── docs/
│   ├── erd.puml
│   ├── use-case.puml
│   ├── microservices-architecture.puml
│   └── PROJECT_STRUCTURE.md
├── scripts/
│   ├── test-workflow.ps1
│   └── README.md
├── tests/
│   ├── README.md
│   ├── unit/
│   ├── integration/
│   └── e2e/                         # HTTP + email sink + concurrency
└── test-workflow.bat
```

**Database logical ownership:** `auth_db` (`users`, `wallet_operations`), `tuition_db` (`tuitions`), `payment_db` (`transactions`, `outbox_events`). Notification has no database. No foreign keys across service-owned databases; inter-service coordination uses HTTP and the Saga/compensation pattern.
