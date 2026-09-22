from pydantic import BaseModel

class TuitionOut(BaseModel):
    student_code: str
    student_name: str
    tuition_fee: float
    is_paid: bool

    class Config:
        from_attributes = True

class TuitionMessage(BaseModel):
    success: bool
    message: str