-- Run on payment_db only, after inspecting existing conflicting active rows.
-- Resolve duplicated pending/processing/compensation_required records before applying.
CREATE UNIQUE INDEX IF NOT EXISTS uq_payment_user_mssv_active
  ON transactions (user_id, mssv)
  WHERE status IN ('pending','processing','compensation_required');
