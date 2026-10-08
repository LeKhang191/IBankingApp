import os
import random
import httpx
from datetime import datetime, timedelta
from fastapi import FastAPI, APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.middleware.cors import CORSMiddleware
from app.models import Base, PaymentTransaction

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/ibanking")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(title="Payment Service")
router = APIRouter(prefix="/api/payments", tags=["payments"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AUTH_SERVICE_URL = "http://auth-service:8001"
TUITION_SERVICE_URL = "http://tuition-service:8001"
NOTIFICATION_SERVICE_URL = "http://notification-service:8003"

class InitPaymentRequest(BaseModel):
    mssv: str

class VerifyOtpRequest(BaseModel):
    transaction_id: str
    otp: str

@router.post("/init")
async def init_payment(payload: InitPaymentRequest, authorization: str = Header(...), db: Session = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        user_res = await client.get(f"{AUTH_SERVICE_URL}/api/auth/me", headers={"Authorization": authorization})
        if user_res.status_code != 200:
            raise HTTPException(status_code=401, detail="Xác thực người dùng thất bại.")
        user_data = user_res.json()

        tuition_res = await client.get(f"{TUITION_SERVICE_URL}/api/tuitions/{payload.mssv}")
        if tuition_res.status_code != 200:
            raise HTTPException(status_code=tuition_res.status_code, detail="Không tìm thấy thông tin học phí.")
        tuition_data = tuition_res.json()
        
        if tuition_data.get("is_paid"):
            raise HTTPException(status_code=400, detail="Học phí này đã được thanh toán.")

        amount = tuition_data.get("tuition_fee") or tuition_data.get("amount")
        if user_data.get("balance", 0) < amount:
            raise HTTPException(status_code=400, detail="Số dư tài khoản không đủ để đóng học phí.")

        otp_code = f"{random.randint(100000, 999999)}"
        txn_id = f"TXN{int(datetime.utcnow().timestamp() * 1000)}"

        txn = PaymentTransaction(
            id=txn_id,
            mssv=payload.mssv,
            student_name=tuition_data.get("student_name", "Sinh viên"),
            amount=amount,
            user_id=str(user_data.get("id")),
            user_email=user_data.get("email"),
            otp=otp_code,
            otp_expires_at=datetime.utcnow() + timedelta(minutes=5),
            status="pending"
        )
        db.add(txn)
        db.commit()

        await client.post(
            f"{NOTIFICATION_SERVICE_URL}/api/notifications/send-otp",
            json={"email": user_data.get("email"), "otp": otp_code, "expires_in_minutes": 5},
            timeout=5.0
        )

        return {"success": True, "transaction_id": txn_id, "message": "Mã OTP đã được gửi đến email của bạn."}

@router.post("/verify-otp")
async def verify_otp(payload: VerifyOtpRequest, authorization: str = Header(...), db: Session = Depends(get_db)):
    txn = db.query(PaymentTransaction).filter(PaymentTransaction.id == payload.transaction_id.strip()).first()
    if not txn:
        print(f"[-] Không tìm thấy transaction_id: {payload.transaction_id}")
        raise HTTPException(status_code=404, detail="Không tìm thấy mã giao dịch.")
    
    if txn.status == "success":
        raise HTTPException(status_code=400, detail="Giao dịch này đã hoàn tất trước đó.")

    input_otp = str(payload.otp).strip()
    db_otp = str(txn.otp).strip()
    print(f"[OTP DEBUG] DB OTP: '{db_otp}' | User Input: '{input_otp}' | Match: {db_otp == input_otp}")

    if datetime.utcnow() > txn.otp_expires_at:
        print(f"[-] OTP đã hết hạn: Hiện tại {datetime.utcnow()} > Hết hạn {txn.otp_expires_at}")
        raise HTTPException(status_code=400, detail="Mã OTP đã hết hiệu lực (quá 5 phút).")

    if db_otp != input_otp:
        raise HTTPException(status_code=400, detail="Mã OTP không chính xác.")

    # Đã thụt lề chuẩn vào trong hàm verify_otp
    async with httpx.AsyncClient() as client:
        deduct_res = await client.post(
            f"{AUTH_SERVICE_URL}/api/auth/deduct",
            json={"amount": txn.amount},
            headers={"Authorization": authorization}
        )
        if deduct_res.status_code != 200:
            error_msg = deduct_res.json().get("detail", "Lỗi trừ tiền tài khoản.")
            raise HTTPException(status_code=deduct_res.status_code, detail=error_msg)

        pay_res = await client.post(f"{TUITION_SERVICE_URL}/api/tuitions/{txn.mssv}/pay")
        
        if pay_res.status_code != 200:
            await client.post(
                f"{AUTH_SERVICE_URL}/api/auth/refund",
                json={"amount": txn.amount},
                headers={"Authorization": authorization}
            )
            pay_error = pay_res.json().get("detail", "Lỗi gạch nợ học phí.")
            raise HTTPException(status_code=pay_res.status_code, detail=f"Thanh toán thất bại: {pay_error}. Số dư đã được hoàn lại.")

        txn.status = "success"
        txn.is_verified = True
        db.commit()

        try:
            await client.post(
                f"{NOTIFICATION_SERVICE_URL}/api/notifications/send-receipt",
                json={
                    "email": txn.user_email,
                    "transaction_id": txn.id,
                    "student_code": txn.mssv,
                    "student_name": txn.student_name,
                    "amount": txn.amount,
                    "created_at": txn.created_at.strftime("%Y-%m-%d %H:%M:%S")
                },
                timeout=5.0
            )
        except Exception as e:
            print(f"[-] Lỗi gửi email biên lai: {e}")

        return {
            "success": True, 
            "message": "Thanh toán học phí thành công!",
            "transaction": {
                "id": txn.id,
                "mssv": txn.mssv,
                "studentName": txn.student_name,
                "amount": txn.amount,
                "createdAt": txn.created_at.isoformat(),
                "status": "success"
            }
        }

@router.get("/history")
def get_payment_history(db: Session = Depends(get_db)):
    txns = db.query(PaymentTransaction).filter(PaymentTransaction.status == "success").order_by(PaymentTransaction.created_at.desc()).all()
    return {
        "success": True,
        "transactions": [
            {
                "id": t.id,
                "mssv": t.mssv,
                "studentName": t.student_name,
                "amount": t.amount,
                "createdAt": t.created_at.isoformat() if t.created_at else None,
                "status": t.status
            }
            for t in txns
        ]
    }

app.include_router(router)