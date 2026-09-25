from pydantic import BaseModel, EmailStr

class SendOtpRequest(BaseModel):
    email: EmailStr
    otp: str
    expires_in_minutes: int = 5

class SendReceiptRequest(BaseModel):
    email: EmailStr
    transaction_id: str
    student_code: str
    student_name: str
    amount: float
    created_at: str