import datetime

from sqlalchemy import Column, String, Numeric, DateTime, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class PaymentTransaction(Base):
    __tablename__ = "transactions"

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
