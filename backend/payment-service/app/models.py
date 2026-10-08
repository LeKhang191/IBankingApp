from sqlalchemy import Column, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class PaymentTransaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, index=True)
    mssv = Column(String, index=True)
    student_name = Column(String)
    amount = Column(Float)
    user_id = Column(String)
    user_email = Column(String)
    otp = Column(String)
    otp_expires_at = Column(DateTime)
    is_verified = Column(Boolean, default=False)
    status = Column(String, default="pending")  
    created_at = Column(DateTime, default=datetime.datetime.utcnow)