from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, CheckConstraint
from app.database import Base


class Tuition(Base):
    __tablename__ = "tuitions"
    __table_args__ = (CheckConstraint("tuition_fee > 0", name="ck_tuitions_positive_fee"),)

    id = Column(Integer, primary_key=True, index=True)
    student_code = Column(String, unique=True, index=True, nullable=False)
    student_name = Column(String, nullable=False)
    tuition_fee = Column(Numeric(18, 2), nullable=False)
    is_paid = Column(Boolean, default=False, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    # Unique transaction id giúp chứng minh một giao dịch chỉ gạch nợ một lần.
    paid_transaction_id = Column(String(64), unique=True, nullable=True)
