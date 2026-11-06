-- Phase 3 migration for the payment_db database.
-- Run as a database owner/superuser before starting the Phase 3 API/worker.

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS debit_applied BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS tuition_settled BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS saga_attempts INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS saga_lease_until TIMESTAMP NULL,
    ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMP NULL,
    ADD COLUMN IF NOT EXISTS last_error TEXT NULL;

-- Existing completed payments are already settled. This prevents historical
-- successful rows from being reconsidered by the recovery worker.
UPDATE public.transactions
SET debit_applied = TRUE,
    tuition_settled = TRUE
WHERE status = 'success';

-- Phase 1/2 used this state only after a debit had already been accepted and
-- the compensation/refund step could not be confirmed. Recover it as debited.
UPDATE public.transactions
SET debit_applied = TRUE
WHERE status = 'compensation_required';

CREATE INDEX IF NOT EXISTS ix_transactions_saga_recovery
    ON public.transactions (status, next_retry_at, saga_lease_until);

CREATE TABLE IF NOT EXISTS public.outbox_events (
    id VARCHAR(64) PRIMARY KEY,
    event_type VARCHAR(80) NOT NULL,
    aggregate_id VARCHAR(64) NOT NULL,
    payload JSON NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    locked_until TIMESTAMP NULL,
    last_error TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP NULL,
    CONSTRAINT uq_outbox_event_aggregate UNIQUE (event_type, aggregate_id)
);

CREATE INDEX IF NOT EXISTS ix_outbox_due
    ON public.outbox_events (status, next_attempt_at, locked_until);
