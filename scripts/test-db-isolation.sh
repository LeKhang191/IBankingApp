#!/bin/sh
set -eu

: "${AUTH_DB_NAME:=auth_db}"; : "${AUTH_DB_USER:=auth_user}"; : "${AUTH_DB_PASSWORD:?}"
: "${TUITION_DB_NAME:=tuition_db}"; : "${TUITION_DB_USER:=tuition_user}"; : "${TUITION_DB_PASSWORD:?}"
: "${PAYMENT_DB_NAME:=payment_db}"; : "${PAYMENT_DB_USER:=payment_user}"; : "${PAYMENT_DB_PASSWORD:?}"

can_connect() {
  user="$1" password="$2" database="$3"
  PGPASSWORD="$password" psql -X -h postgres -U "$user" -d "$database" -A -t -c 'SELECT 1;' >/dev/null 2>&1
}

must_connect() {
  if ! can_connect "$1" "$2" "$3"; then
    echo "FAIL: $1 cannot connect to its owned database $3" >&2
    exit 1
  fi
  echo "PASS: $1 connects to owned database $3"
}

must_not_connect() {
  if can_connect "$1" "$2" "$3"; then
    echo "FAIL: $1 can unexpectedly connect to non-owned database $3" >&2
    exit 1
  fi
  echo "PASS: $1 cannot connect to non-owned database $3"
}

must_connect "$AUTH_DB_USER" "$AUTH_DB_PASSWORD" "$AUTH_DB_NAME"
must_connect "$TUITION_DB_USER" "$TUITION_DB_PASSWORD" "$TUITION_DB_NAME"
must_connect "$PAYMENT_DB_USER" "$PAYMENT_DB_PASSWORD" "$PAYMENT_DB_NAME"
must_not_connect "$AUTH_DB_USER" "$AUTH_DB_PASSWORD" "$TUITION_DB_NAME"
must_not_connect "$AUTH_DB_USER" "$AUTH_DB_PASSWORD" "$PAYMENT_DB_NAME"
must_not_connect "$TUITION_DB_USER" "$TUITION_DB_PASSWORD" "$AUTH_DB_NAME"
must_not_connect "$TUITION_DB_USER" "$TUITION_DB_PASSWORD" "$PAYMENT_DB_NAME"
must_not_connect "$PAYMENT_DB_USER" "$PAYMENT_DB_PASSWORD" "$AUTH_DB_NAME"
must_not_connect "$PAYMENT_DB_USER" "$PAYMENT_DB_PASSWORD" "$TUITION_DB_NAME"

echo 'PASS: database ownership isolation checks completed.'
