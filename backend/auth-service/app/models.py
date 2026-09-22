from sqlalchemy import Column, String, BigInteger, Numeric

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=False)
    # Lưu ý: trong hệ thống thật, số dư nên nằm ở payment-service/ledger riêng.
    # Để đơn giản hoá đồ án, tạm lưu chung ở đây và cho payment-service đọc qua API.
    balance = Column(Numeric(18, 2), nullable=False, default=0)