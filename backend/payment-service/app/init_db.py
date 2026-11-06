"""Single-owner payment database setup, run before API and worker start.

Never run schema creation as a side effect of importing app.main. The worker
imports app.main too, so startup-time create_all caused PostgreSQL DDL races.
"""

import logging
import os
from pathlib import Path

from sqlalchemy import create_engine

from app.models import Base

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("ibanking.payment.database")

MIGRATION_DIRECTORY = Path(os.getenv("PAYMENT_MIGRATIONS_DIR", "/database/migrations/payment"))
DATABASE_URL = os.environ["DATABASE_URL"]


def initialize() -> None:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    try:
        # The session-level advisory lock also protects accidental concurrent
        # manual init runs. Both new schema and migrations are guarded.
        raw = engine.raw_connection()
        try:
            with raw.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_lock(204826, 1)")
            raw.commit()
            try:
                with engine.begin() as connection:
                    Base.metadata.create_all(bind=connection, checkfirst=True)
                logger.info("Payment tables ready")

                for script in sorted(MIGRATION_DIRECTORY.glob("*.sql")):
                    # PostgreSQL / psycopg supports semicolon-delimited SQL
                    # including DO $$ blocks. Commit per migration file.
                    with raw.cursor() as cursor:
                        cursor.execute(script.read_text(encoding="utf-8"))
                    raw.commit()
                    logger.info("Applied/verified payment migration %s", script.name)
            finally:
                with raw.cursor() as cursor:
                    cursor.execute("SELECT pg_advisory_unlock(204826, 1)")
                raw.commit()
        finally:
            raw.close()
    finally:
        engine.dispose()


if __name__ == "__main__":
    initialize()
