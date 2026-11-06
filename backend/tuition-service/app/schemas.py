from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class TuitionOut(BaseModel):
    student_code: str
    student_name: str
    tuition_fee: Decimal
    is_paid: bool
    paid_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TuitionMessage(BaseModel):
    success: bool
    message: str
