-- Run once on auth_db after auditing existing balances/operations.
-- Constraints are idempotent even for existing installations.
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='ck_users_nonnegative_balance') THEN
   ALTER TABLE users ADD CONSTRAINT ck_users_nonnegative_balance CHECK (balance >= 0);
 END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='ck_wallet_positive_amount') THEN
   ALTER TABLE wallet_operations ADD CONSTRAINT ck_wallet_positive_amount CHECK (amount > 0);
 END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='ck_wallet_operation_type') THEN
   ALTER TABLE wallet_operations ADD CONSTRAINT ck_wallet_operation_type CHECK (operation IN ('DEBIT','REFUND'));
 END IF;
END $$;
