import datetime

from sqlalchemy import (
    Column,
    String,
    Numeric,
    DateTime,
    Boolean,
    Integer,
    Text,
    JSON,
    UniqueConstraint,
    Index,
    CheckConstraint,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class PaymentTransaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payments_positive_amount"),
        CheckConstraint("otp_attempts >= 0 AND otp_resend_count >= 0", name="ck_payments_otp_counters"),
    )

    id = Column(String(64), primary_key=True, index=True)
    mssv = Column(String(20), nullable=False, index=True)
    student_name = Column(String(255), nullable=False)
    amount = Column(Numeric(18, 2), nullable=False)
    user_id = Column(String(64), nullable=False, index=True)
    user_email = Column(String(255), nullable=False)
    otp_hash = Column(String(64), nullable=False)
    otp_expires_at = Column(DateTime, nullable=False)
    otp_attempts = Column(Integer, nullable=False, default=0)
    otp_resend_count = Column(Integer, nullable=False, default=0)
    otp_last_sent_at = Column(DateTime, nullable=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    status = Column(String(32), nullable=False, default="pending", index=True)
    processing_at = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # Saga progress. Each remote operation is idempotent on transaction id;
    # these flags let recovery resume from the last confirmed step.
    debit_applied = Column(Boolean, nullable=False, default=False)
    tuition_settled = Column(Boolean, nullable=False, default=False)
    saga_attempts = Column(Integer, nullable=False, default=0)
    saga_lease_until = Column(DateTime, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        UniqueConstraint("event_type", "aggregate_id", name="uq_outbox_event_aggregate"),
        Index("ix_outbox_due", "status", "next_attempt_at", "locked_until"),
    )

    id = Column(String(64), primary_key=True)
    event_type = Column(String(80), nullable=False)
    aggregate_id = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    locked_until = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
