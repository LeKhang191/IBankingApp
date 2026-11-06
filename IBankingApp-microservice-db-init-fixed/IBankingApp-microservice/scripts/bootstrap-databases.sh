#!/bin/sh
set -eu

: "${PGHOST:=postgres}"
: "${PGPORT:=5432}"
: "${PGUSER:=postgres}"
: "${PGPASSWORD:?POSTGRES_PASSWORD is required for database bootstrap}"
: "${POSTGRES_DB:=ibanking}"
: "${AUTH_DB_NAME:=auth_db}"
: "${AUTH_DB_USER:=auth_user}"
: "${AUTH_DB_PASSWORD:?AUTH_DB_PASSWORD is required}"
: "${TUITION_DB_NAME:=tuition_db}"
: "${TUITION_DB_USER:=tuition_user}"
: "${TUITION_DB_PASSWORD:?TUITION_DB_PASSWORD is required}"
: "${PAYMENT_DB_NAME:=payment_db}"
: "${PAYMENT_DB_USER:=payment_user}"
: "${PAYMENT_DB_PASSWORD:?PAYMENT_DB_PASSWORD is required}"

psql --no-psqlrc --set ON_ERROR_STOP=1 \
  --dbname="$POSTGRES_DB" \
  --set=auth_db_name="$AUTH_DB_NAME" \
  --set=auth_db_user="$AUTH_DB_USER" \
  --set=auth_db_password="$AUTH_DB_PASSWORD" \
  --set=tuition_db_name="$TUITION_DB_NAME" \
  --set=tuition_db_user="$TUITION_DB_USER" \
  --set=tuition_db_password="$TUITION_DB_PASSWORD" \
  --set=payment_db_name="$PAYMENT_DB_NAME" \
  --set=payment_db_user="$PAYMENT_DB_USER" \
  --set=payment_db_password="$PAYMENT_DB_PASSWORD" \
  --file=/scripts/bootstrap-databases.sql

# The database owner can create its own tables in the public schema. Remove
# CREATE from PUBLIC so an unrelated service role cannot create objects here.
for database in "$AUTH_DB_NAME" "$TUITION_DB_NAME" "$PAYMENT_DB_NAME"; do
  psql --no-psqlrc --set ON_ERROR_STOP=1 --dbname="$database" \
    --command='REVOKE CREATE ON SCHEMA public FROM PUBLIC;'
done

echo "Database bootstrap completed: $AUTH_DB_NAME, $TUITION_DB_NAME, $PAYMENT_DB_NAME"
