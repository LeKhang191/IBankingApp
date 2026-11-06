-- Run on payment_db after initial Phase 3 migration.
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='ck_payments_positive_amount') THEN
  ALTER TABLE transactions ADD CONSTRAINT ck_payments_positive_amount CHECK (amount > 0);
 END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='ck_payments_otp_counters') THEN
  ALTER TABLE transactions ADD CONSTRAINT ck_payments_otp_counters CHECK (otp_attempts >= 0 AND otp_resend_count >= 0);
 END IF;
END $$;
