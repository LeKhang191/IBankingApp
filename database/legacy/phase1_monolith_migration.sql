-- Run against the existing ibanking database BEFORE rebuilding the services.
-- Back up the database first. This migration preserves the legacy otp column for now.

-- Tuition fields missing from the current ORM model but referenced by the pay endpoint.
ALTER TABLE IF EXISTS tuitions
    ADD COLUMN IF NOT EXISTS paid_at TIMESTAMP NULL;

ALTER TABLE IF EXISTS tuitions
    ADD COLUMN IF NOT EXISTS paid_transaction_id VARCHAR(64) NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_tuitions_paid_transaction_id
    ON tuitions (paid_transaction_id)
    WHERE paid_transaction_id IS NOT NULL;

-- Payment Service OTP and processing metadata.
ALTER TABLE IF EXISTS transactions
    ADD COLUMN IF NOT EXISTS otp_hash VARCHAR(64);

ALTER TABLE IF EXISTS transactions
    ADD COLUMN IF NOT EXISTS otp_attempts INTEGER NOT NULL DEFAULT 0;

ALTER TABLE IF EXISTS transactions
    ADD COLUMN IF NOT EXISTS otp_resend_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE IF EXISTS transactions
    ADD COLUMN IF NOT EXISTS otp_last_sent_at TIMESTAMP NULL;

ALTER TABLE IF EXISTS transactions
    ADD COLUMN IF NOT EXISTS processing_at TIMESTAMP NULL;

ALTER TABLE IF EXISTS transactions
    ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP NULL;

ALTER TABLE IF EXISTS transactions
    ALTER COLUMN amount TYPE NUMERIC(18, 2) USING amount::NUMERIC(18, 2);

-- The new OTP hash cannot be inferred securely from a legacy plaintext OTP after deployment.
-- Pending legacy transactions must be expired/cancelled; users should start a new payment.
UPDATE transactions
SET status = 'expired'
WHERE status = 'pending' AND otp_hash IS NULL;
