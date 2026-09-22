from sqlalchemy import Column, Integer, String, Float, Boolean
from app.database import Base

class Tuition(Base):
    __tablename__ = "tuitions"

    id = Column(Integer, primary_key=True, index=True)
    student_code = Column(String, unique=True, index=True, nullable=False) # MSSV
    student_name = Column(String, nullable=False)
    tuition_fee = Column(Float, nullable=False)
    is_paid = Column(Boolean, default=False)