import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import httpx
from fastapi import FastAPI, APIRouter, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.models import Base, PaymentTransaction

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/ibanking")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001")
TUITION_SERVICE_URL = os.getenv("TUITION_SERVICE_URL", "http://tuition-service:8001")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8003")
INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "")
OTP_PEPPER = os.getenv("OTP_PEPPER", "")
OTP_EXPIRE_MINUTES = int(os.getenv("OTP_EXPIRE_MINUTES", "5"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
OTP_MAX_RESENDS = int(os.getenv("OTP_MAX_RESENDS", "3"))
OTP_RESEND_COOLDOWN_SECONDS = int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "30"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI(title="Payment Service", version="2.0.0")
router = APIRouter(prefix="/api/payments", tags=["payments"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173").split(",") if x.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Internal-Token"],
)


class InitPaymentRequest(BaseModel):
    mssv: str = Field(min_length=5, max_length=20, pattern=r"^[0-9]+$")


class VerifyOtpRequest(BaseModel):
    transaction_id: str = Field(min_length=8, max_length=64)
    otp: str = Field(min_length=6, max_length=6, pattern=r"^[0-9]{6}$")


def otp_digest(otp: str) -> str:
    if not OTP_PEPPER:
        raise HTTPException(status_code=503, detail="OTP_PEPPER chưa được cấu hình.")
    return hmac.new(OTP_PEPPER.encode("utf-8"), otp.encode("ascii"), hashlib.sha256).hexdigest()


def internal_headers() -> dict:
    if not INTERNAL_SERVICE_TOKEN:
        raise HTTPException(status_code=503, detail="INTERNAL_SERVICE_TOKEN chưa được cấu hình.")
    return {"X-Internal-Token": INTERNAL_SERVICE_TOKEN}


async def get_user_data(authorization: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                f"{AUTH_SERVICE_URL}/api/auth/me",
                headers={"Authorization": authorization},
            )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail="Auth Service hiện không khả dụng.") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Xác thực người dùng thất bại.")
    return response.json()


def transaction_result(txn: PaymentTransaction) -> dict:
    return {
        "id": txn.id,
        "mssv": txn.mssv,
        "studentName": txn.student_name,
        "amount": float(txn.amount),
        "createdAt": txn.created_at.isoformat() if txn.created_at else None,
        "status": txn.status,
    }


@router.post("/init", status_code=201)
async def init_payment(
    payload: InitPaymentRequest,
    authorization: str = Header(...),
    db: Session = Depends(get_db),
):
    if not OTP_PEPPER:
        raise HTTPException(status_code=503, detail="OTP_PEPPER chưa được cấu hình.")
    user_data = await get_user_data(authorization)

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            tuition_res = await client.get(f"{TUITION_SERVICE_URL}/api/tuitions/{payload.mssv}")
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail="Tuition Service hiện không khả dụng.") from exc

    if tuition_res.status_code != 200:
        raise HTTPException(status_code=tuition_res.status_code, detail="Không tìm thấy thông tin học phí.")

    tuition_data = tuition_res.json()
    if tuition_data.get("is_paid"):
        raise HTTPException(status_code=409, detail="Học phí này đã được thanh toán.")

    amount = Decimal(str(tuition_data.get("tuition_fee", tuition_data.get("amount", 0))))
    balance = Decimal(str(user_data.get("balance", 0)))
    if amount <= 0:
        raise HTTPException(status_code=422, detail="Số tiền học phí không hợp lệ.")
    if balance < amount:
        raise HTTPException(status_code=400, detail="Số dư tài khoản không đủ để đóng học phí.")

    # Không tạo thêm pending transaction trùng cho cùng người dùng/MSSV.
    existing = (
        db.query(PaymentTransaction)
        .filter(
            PaymentTransaction.user_id == str(user_data["id"]),
            PaymentTransaction.mssv == payload.mssv,
            PaymentTransaction.status.in_(["pending", "processing"]),
        )
        .order_by(PaymentTransaction.created_at.desc())
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Bạn đang có giao dịch chờ xử lý: {existing.id}.")

    otp = f"{secrets.randbelow(900000) + 100000:06d}"
    now = datetime.utcnow()
    txn = PaymentTransaction(
        id=f"TXN-{uuid.uuid4().hex}",
        mssv=payload.mssv,
        student_name=tuition_data.get("student_name", "Sinh viên"),
        amount=amount,
        user_id=str(user_data["id"]),
        user_email=user_data["email"],
        otp_hash=otp_digest(otp),
        otp_expires_at=now + timedelta(minutes=OTP_EXPIRE_MINUTES),
        otp_attempts=0,
        otp_resend_count=0,
        otp_last_sent_at=now,
        status="pending",
        created_at=now,
    )
    db.add(txn)
    db.commit()

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            notify_res = await client.post(
                f"{NOTIFICATION_SERVICE_URL}/api/notifications/send-otp",
                json={"email": user_data["email"], "otp": otp, "expires_in_minutes": OTP_EXPIRE_MINUTES},
                headers=internal_headers(),
            )
        notify_res.raise_for_status()
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        txn.status = "failed"
        db.commit()
        raise HTTPException(status_code=503, detail="Không gửi được OTP. Vui lòng khởi tạo lại giao dịch.") from exc

    return {
        "success": True,
        "transaction_id": txn.id,
        "expires_in_seconds": OTP_EXPIRE_MINUTES * 60,
        "message": "Mã OTP đã được gửi đến email của bạn.",
    }


@router.post("/resend-otp/{transaction_id}")
async def resend_otp(
    transaction_id: str,
    authorization: str = Header(...),
    db: Session = Depends(get_db),
):
    user_data = await get_user_data(authorization)
    txn = (
        db.query(PaymentTransaction)
        .filter(PaymentTransaction.id == transaction_id)
        .with_for_update()
        .first()
    )
    if not txn or txn.user_id != str(user_data["id"]):
        raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch.")
    if txn.status != "pending":
        raise HTTPException(status_code=409, detail="Giao dịch không còn ở trạng thái chờ OTP.")
    if txn.otp_resend_count >= OTP_MAX_RESENDS:
        raise HTTPException(status_code=429, detail="Bạn đã vượt quá số lần gửi lại OTP.")

    now = datetime.utcnow()
    if txn.otp_last_sent_at and (now - txn.otp_last_sent_at).total_seconds() < OTP_RESEND_COOLDOWN_SECONDS:
        raise HTTPException(status_code=429, detail=f"Vui lòng chờ {OTP_RESEND_COOLDOWN_SECONDS} giây giữa hai lần gửi OTP.")

    otp = f"{secrets.randbelow(900000) + 100000:06d}"
    txn.otp_hash = otp_digest(otp)
    txn.otp_expires_at = now + timedelta(minutes=OTP_EXPIRE_MINUTES)
    txn.otp_attempts = 0
    txn.otp_resend_count += 1
    txn.otp_last_sent_at = now
    db.commit()

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                f"{NOTIFICATION_SERVICE_URL}/api/notifications/send-otp",
                json={"email": txn.user_email, "otp": otp, "expires_in_minutes": OTP_EXPIRE_MINUTES},
                headers=internal_headers(),
            )
        response.raise_for_status()
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        raise HTTPException(status_code=503, detail="Không gửi được OTP mới. Vui lòng thử lại.") from exc

    return {"success": True, "transaction_id": txn.id, "expires_in_seconds": OTP_EXPIRE_MINUTES * 60}


@router.post("/verify-otp")
async def verify_otp(
    payload: VerifyOtpRequest,
    authorization: str = Header(...),
    db: Session = Depends(get_db),
):
    user_data = await get_user_data(authorization)
    now = datetime.utcnow()
    txn = (
        db.query(PaymentTransaction)
        .filter(PaymentTransaction.id == payload.transaction_id.strip())
        .with_for_update()
        .first()
    )
    if not txn or txn.user_id != str(user_data["id"]):
        # Không tiết lộ transaction có tồn tại nhưng thuộc tài khoản khác.
        raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch.")

    if txn.status == "success":
        return {"success": True, "message": "Giao dịch đã hoàn tất trước đó.", "transaction": transaction_result(txn)}
    if txn.status in ["failed", "otp_locked", "expired", "compensation_required"]:
        raise HTTPException(status_code=409, detail=f"Giao dịch đang ở trạng thái {txn.status}.")

    if txn.status == "pending":
        if now > txn.otp_expires_at:
            txn.status = "expired"
            db.commit()
            raise HTTPException(status_code=400, detail="Mã OTP đã hết hiệu lực.")

        expected = txn.otp_hash
        actual = otp_digest(payload.otp)
        if not hmac.compare_digest(expected, actual):
            txn.otp_attempts += 1
            if txn.otp_attempts >= OTP_MAX_ATTEMPTS:
                txn.status = "otp_locked"
            db.commit()
            if txn.status == "otp_locked":
                raise HTTPException(status_code=429, detail="Bạn đã nhập sai OTP quá số lần cho phép.")
            raise HTTPException(status_code=400, detail="Mã OTP không chính xác.")

        txn.is_verified = True
        txn.status = "processing"
        txn.processing_at = now
        db.commit()
    elif txn.status == "processing":
        # Cho phép retry sau timeout/crash; các bước debit/pay đều idempotent.
        # Không xác minh lại OTP vì transaction đã được xác minh và khóa trạng thái.
        if txn.processing_at and (now - txn.processing_at).total_seconds() < 15:
            raise HTTPException(status_code=409, detail="Giao dịch đang được xử lý. Vui lòng không gửi lặp liên tục.")
        txn.processing_at = now
        db.commit()
    else:
        raise HTTPException(status_code=409, detail="Trạng thái giao dịch không hợp lệ.")

    # Bước 1: trừ tiền idempotent tại Auth Service.
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            debit_res = await client.post(
                f"{AUTH_SERVICE_URL}/api/auth/deduct",
                json={"user_id": txn.user_id, "amount": str(txn.amount), "transaction_id": txn.id},
                headers=internal_headers(),
            )
    except httpx.RequestError as exc:
        # Giữ processing để retry bằng cùng transaction_id, không tạo debit mới.
        raise HTTPException(status_code=503, detail="Auth Service timeout. Có thể thử xác nhận lại cùng giao dịch.") from exc

    if debit_res.status_code != 200:
        if debit_res.status_code < 500:
            txn.status = "failed"
            db.commit()
        raise HTTPException(status_code=debit_res.status_code, detail=debit_res.json().get("detail", "Không thể trừ tiền."))

    # Bước 2: gạch nợ idempotent tại Tuition Service.
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            pay_res = await client.post(
                f"{TUITION_SERVICE_URL}/api/tuitions/{txn.mssv}/pay",
                json={"transaction_id": txn.id},
                headers=internal_headers(),
            )
    except httpx.RequestError as exc:
        # Kết quả không rõ: không refund mù vì Tuition có thể đã commit.
        raise HTTPException(status_code=503, detail="Tuition Service timeout. Hãy retry cùng giao dịch để đối soát.") from exc

    if pay_res.status_code != 200:
        if pay_res.status_code >= 500:
            raise HTTPException(status_code=503, detail="Tuition Service lỗi tạm thời. Hãy retry cùng giao dịch.")

        # Definitive failure: bù trừ debit. Refund cũng idempotent.
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                refund_res = await client.post(
                    f"{AUTH_SERVICE_URL}/api/auth/refund",
                    json={"user_id": txn.user_id, "amount": str(txn.amount), "transaction_id": txn.id},
                    headers=internal_headers(),
                )
            refund_res.raise_for_status()
            txn.status = "failed"
            db.commit()
            raise HTTPException(status_code=pay_res.status_code, detail=f"Thanh toán bị từ chối; số dư đã được hoàn. {pay_res.json().get('detail', '')}")
        except httpx.HTTPStatusError as exc:
            txn.status = "compensation_required"
            db.commit()
            raise HTTPException(status_code=500, detail="Thanh toán lỗi và hoàn tiền chưa thành công; cần đối soát giao dịch.") from exc
        except httpx.RequestError as exc:
            txn.status = "compensation_required"
            db.commit()
            raise HTTPException(status_code=503, detail="Không kết nối được Auth Service để hoàn tiền; cần đối soát giao dịch.") from exc

    txn.status = "success"
    txn.processed_at = datetime.utcnow()
    db.commit()
    db.refresh(txn)

    # Email biên lai là side-effect sau thanh toán; lỗi email không rollback thanh toán.
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            await client.post(
                f"{NOTIFICATION_SERVICE_URL}/api/notifications/send-receipt",
                json={
                    "email": txn.user_email,
                    "transaction_id": txn.id,
                    "student_code": txn.mssv,
                    "student_name": txn.student_name,
                    "amount": float(txn.amount),
                    "created_at": txn.processed_at.strftime("%Y-%m-%d %H:%M:%S"),
                },
                headers=internal_headers(),
            )
    except (httpx.RequestError, HTTPException):
        # Phase tiếp theo sẽ đưa receipt vào transactional outbox để retry bền vững.
        pass

    return {
        "success": True,
        "message": "Thanh toán học phí thành công!",
        "transaction": transaction_result(txn),
    }


@router.get("/history")
async def get_payment_history(
    authorization: str = Header(...),
    db: Session = Depends(get_db),
):
    user_data = await get_user_data(authorization)
    txns = (
        db.query(PaymentTransaction)
        .filter(
            PaymentTransaction.user_id == str(user_data["id"]),
            PaymentTransaction.status == "success",
        )
        .order_by(PaymentTransaction.created_at.desc())
        .all()
    )
    return {"success": True, "transactions": [transaction_result(txn) for txn in txns]}


app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "payment-service"}
