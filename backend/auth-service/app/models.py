from sqlalchemy import Column, String, Numeric, Integer, DateTime, UniqueConstraint, CheckConstraint
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("balance >= 0", name="ck_users_nonnegative_balance"),)

    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=False)
    # Số dư dùng Numeric để tránh sai số dấu phẩy động khi tính tiền.
    balance = Column(Numeric(18, 2), nullable=False, default=0)


class WalletOperation(Base):
    """Sổ ghi nhận thao tác ví để một transaction không bị trừ/hoàn nhiều lần."""
    __tablename__ = "wallet_operations"
    __table_args__ = (
        UniqueConstraint("transaction_id", "operation", name="uq_wallet_txn_operation"),
        CheckConstraint("amount > 0", name="ck_wallet_positive_amount"),
        CheckConstraint("operation IN ('DEBIT', 'REFUND')", name="ck_wallet_operation_type"),
    )

    id = Column(Integer, primary_key=True)
    transaction_id = Column(String(64), nullable=False, index=True)
    operation = Column(String(16), nullable=False)  # DEBIT hoặc REFUND
    user_id = Column(String, nullable=False, index=True)
    amount = Column(Numeric(18, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
