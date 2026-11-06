#!/bin/sh
# Copy Phase 1 rows from the shared ibanking DB into the Phase 2 owned DBs.
# Run only after the three backend services have created their target schemas
# and with SEED_DEMO_DATA=false. Target service tables are truncated first.
set -eu

PGUSER="${POSTGRES_USER:-postgres}"
LEGACY_DB="${POSTGRES_DB:-ibanking}"
AUTH_DB="${AUTH_DB_NAME:-auth_db}"
TUITION_DB="${TUITION_DB_NAME:-tuition_db}"
PAYMENT_DB="${PAYMENT_DB_NAME:-payment_db}"

check_table() {
  table="$1"
  exists="$(psql -X -A -t -U "$PGUSER" -d "$LEGACY_DB" -c "SELECT to_regclass('public.$table') IS NOT NULL;")"
  if [ "$exists" != "t" ]; then
    echo "Missing legacy table public.$table in database $LEGACY_DB" >&2
    exit 1
  fi
}

for table in users wallet_operations tuitions transactions; do
  check_table "$table"
done

# Auth Service owns users and the wallet operation ledger.
pg_dump -U "$PGUSER" -d "$LEGACY_DB" --data-only --no-owner --no-privileges \
  --table=public.users --table=public.wallet_operations > /tmp/phase2-auth-data.sql
psql -X -v ON_ERROR_STOP=1 -U "$PGUSER" -d "$AUTH_DB" \
  -c 'TRUNCATE TABLE wallet_operations, users RESTART IDENTITY CASCADE;'
psql -X -v ON_ERROR_STOP=1 -U "$PGUSER" -d "$AUTH_DB" -f /tmp/phase2-auth-data.sql

# Tuition Service owns the tuition ledger.
pg_dump -U "$PGUSER" -d "$LEGACY_DB" --data-only --no-owner --no-privileges \
  --table=public.tuitions > /tmp/phase2-tuition-data.sql
psql -X -v ON_ERROR_STOP=1 -U "$PGUSER" -d "$TUITION_DB" \
  -c 'TRUNCATE TABLE tuitions RESTART IDENTITY CASCADE;'
psql -X -v ON_ERROR_STOP=1 -U "$PGUSER" -d "$TUITION_DB" -f /tmp/phase2-tuition-data.sql

# Payment Service's Phase 1 legacy table can still contain the old plaintext
# otp column. Export only columns that exist in the current Payment model.
# A zero digest is assigned only to legacy rows without otp_hash; such rows
# were expired by the Phase 1 migration and cannot be used to authenticate.
psql -X -v ON_ERROR_STOP=1 -U "$PGUSER" -d "$LEGACY_DB" <<'SQL'
\copy (SELECT id, mssv, student_name, amount, user_id, user_email, COALESCE(otp_hash, repeat('0', 64)), otp_expires_at, COALESCE(otp_attempts, 0), COALESCE(otp_resend_count, 0), otp_last_sent_at, COALESCE(is_verified, FALSE), COALESCE(status, 'expired'), processing_at, processed_at, created_at FROM public.transactions ORDER BY created_at) TO '/tmp/phase2-payment-data.csv' WITH (FORMAT csv)
SQL
psql -X -v ON_ERROR_STOP=1 -U "$PGUSER" -d "$PAYMENT_DB" \
  -c 'TRUNCATE TABLE transactions;'
psql -X -v ON_ERROR_STOP=1 -U "$PGUSER" -d "$PAYMENT_DB" <<'SQL'
\copy public.transactions (id, mssv, student_name, amount, user_id, user_email, otp_hash, otp_expires_at, otp_attempts, otp_resend_count, otp_last_sent_at, is_verified, status, processing_at, processed_at, created_at) FROM '/tmp/phase2-payment-data.csv' WITH (FORMAT csv)
SQL

echo "Phase 2 data migration completed from $LEGACY_DB to $AUTH_DB, $TUITION_DB, and $PAYMENT_DB."
