import asyncio
import hashlib
import hmac
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import httpx
from fastapi import FastAPI, APIRouter, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, Session

from app.models import Base, OutboxEvent, PaymentTransaction
from app.observability import outbound_headers

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("ibanking.payment")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://payment_user:change_me@postgres:5432/payment_db")
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001")
TUITION_SERVICE_URL = os.getenv("TUITION_SERVICE_URL", "http://tuition-service:8001")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8003")
INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "")
OTP_PEPPER = os.getenv("OTP_PEPPER", "")
OTP_EXPIRE_MINUTES = int(os.getenv("OTP_EXPIRE_MINUTES", "5"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
OTP_MAX_RESENDS = int(os.getenv("OTP_MAX_RESENDS", "3"))
OTP_RESEND_COOLDOWN_SECONDS = int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "30"))
SAGA_LEASE_SECONDS = int(os.getenv("SAGA_LEASE_SECONDS", "90"))
SAGA_RETRY_SECONDS = int(os.getenv("SAGA_RETRY_SECONDS", "10"))
OUTBOX_POLL_SECONDS = float(os.getenv("OUTBOX_POLL_SECONDS", "3"))
OUTBOX_LEASE_SECONDS = int(os.getenv("OUTBOX_LEASE_SECONDS", "60"))

TERMINAL_STATUSES = {"success", "failed", "otp_locked", "expired"}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI(title="Payment Service", version="3.0.0")

from app.observability import install_request_logging
install_request_logging(app, "payment-service")
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
    return outbound_headers({"X-Internal-Token": INTERNAL_SERVICE_TOKEN})


async def get_user_data(authorization: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                f"{AUTH_SERVICE_URL}/api/auth/me",
                headers=outbound_headers({"Authorization": authorization}),
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
        "processedAt": txn.processed_at.isoformat() if txn.processed_at else None,
        "status": txn.status,
    }


def _get_transaction_snapshot(transaction_id: str):
    with SessionLocal() as db:
        txn = db.query(PaymentTransaction).filter(PaymentTransaction.id == transaction_id).first()
        if not txn:
            return None
        return {
            "id": txn.id,
            "mssv": txn.mssv,
            "amount": str(txn.amount),
            "user_id": txn.user_id,
            "user_email": txn.user_email,
            "student_name": txn.student_name,
            "status": txn.status,
            "debit_applied": bool(txn.debit_applied),
            "tuition_settled": bool(txn.tuition_settled),
            "saga_lease_until": txn.saga_lease_until,
            "next_retry_at": txn.next_retry_at,
            "last_error": txn.last_error,
        }


def _claim_saga(transaction_id: str):
    """Acquire a short database lease so API retries and the worker do not run one Saga together."""
    now = datetime.utcnow()
    with SessionLocal() as db:
        txn = (
            db.query(PaymentTransaction)
            .filter(PaymentTransaction.id == transaction_id)
            .with_for_update()
            .first()
        )
        if not txn or txn.status not in {"processing", "compensation_required"}:
            return None
        if txn.saga_lease_until and txn.saga_lease_until > now:
            return None
        if txn.next_retry_at and txn.next_retry_at > now:
            return None

        txn.saga_lease_until = now + timedelta(seconds=SAGA_LEASE_SECONDS)
        txn.saga_attempts = int(txn.saga_attempts or 0) + 1
        txn.next_retry_at = None
        db.commit()
        return {
            "id": txn.id,
            "mssv": txn.mssv,
            "amount": str(txn.amount),
            "user_id": txn.user_id,
            "user_email": txn.user_email,
            "student_name": txn.student_name,
            "status": txn.status,
            "debit_applied": bool(txn.debit_applied),
            "tuition_settled": bool(txn.tuition_settled),
            "last_error": txn.last_error,
        }


def _update_transaction(transaction_id: str, **values):
    with SessionLocal() as db:
        txn = (
            db.query(PaymentTransaction)
            .filter(PaymentTransaction.id == transaction_id)
            .with_for_update()
            .first()
        )
        if not txn:
            return None
        for key, value in values.items():
            setattr(txn, key, value)
        db.commit()
        db.refresh(txn)
        return transaction_result(txn)


def _schedule_saga_retry(transaction_id: str, message: str, status: str = "processing"):
    logger.warning("Saga retry scheduled transaction_id=%s status=%s reason=%s", transaction_id, status, message)
    return _update_transaction(
        transaction_id,
        status=status,
        last_error=message[:2000],
        next_retry_at=datetime.utcnow() + timedelta(seconds=SAGA_RETRY_SECONDS),
        saga_lease_until=None,
    )


def _mark_saga_failed(transaction_id: str, message: str):
    logger.warning("Saga failed transaction_id=%s reason=%s", transaction_id, message)
    return _update_transaction(
        transaction_id,
        status="failed",
        last_error=message[:2000],
        processed_at=datetime.utcnow(),
        next_retry_at=None,
        saga_lease_until=None,
    )


def _mark_compensation_required(transaction_id: str, message: str):
    return _update_transaction(
        transaction_id,
        status="compensation_required",
        last_error=message[:2000],
        next_retry_at=None,
        saga_lease_until=datetime.utcnow() + timedelta(seconds=SAGA_LEASE_SECONDS),
    )


def _enqueue_receipt(db: Session, txn: PaymentTransaction):
    existing = (
        db.query(OutboxEvent)
        .filter(
            OutboxEvent.event_type == "payment.receipt",
            OutboxEvent.aggregate_id == txn.id,
        )
        .first()
    )
    if existing:
        return
    payload = {
        "email": txn.user_email,
        "transaction_id": txn.id,
        "student_code": txn.mssv,
        "student_name": txn.student_name,
        "amount": float(txn.amount),
        "created_at": (txn.processed_at or datetime.utcnow()).strftime("%Y-%m-%d %H:%M:%S"),
    }
    db.add(OutboxEvent(
        id=f"OUT-{uuid.uuid4().hex}",
        event_type="payment.receipt",
        aggregate_id=txn.id,
        payload=payload,
        status="pending",
        attempts=0,
        next_attempt_at=datetime.utcnow(),
    ))


def _mark_saga_success(transaction_id: str):
    with SessionLocal() as db:
        txn = (
            db.query(PaymentTransaction)
            .filter(PaymentTransaction.id == transaction_id)
            .with_for_update()
            .first()
        )
        if not txn:
            return None
        if txn.status != "success":
            txn.status = "success"
            txn.processed_at = datetime.utcnow()
            txn.last_error = None
            txn.next_retry_at = None
            txn.saga_lease_until = None
            _enqueue_receipt(db, txn)
            db.commit()
        else:
            # Defensive repair: if a legacy successful row has no receipt event,
            # create it without changing the successful payment state.
            _enqueue_receipt(db, txn)
            db.commit()
        db.refresh(txn)
        return transaction_result(txn)


async def _compensate_debit(snapshot: dict):
    transaction_id = snapshot["id"]
    if not snapshot["debit_applied"]:
        return _mark_saga_failed(transaction_id, snapshot.get("last_error") or "Không cần hoàn tiền vì chưa ghi nhận debit.")

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.post(
                f"{AUTH_SERVICE_URL}/api/auth/refund",
                json={
                    "user_id": snapshot["user_id"],
                    "amount": snapshot["amount"],
                    "transaction_id": transaction_id,
                },
                headers=internal_headers(),
            )
    except httpx.RequestError as exc:
        _schedule_saga_retry(transaction_id, f"Refund timeout/network error: {exc}", status="compensation_required")
        return _get_transaction_snapshot(transaction_id)

    if response.status_code == 200:
        result = _mark_saga_failed(transaction_id, f"Đã hoàn tiền do bước gạch nợ thất bại: {snapshot.get('last_error', '')}")
        logger.info("Saga compensation completed transaction_id=%s", transaction_id)
        return result

    _schedule_saga_retry(
        transaction_id,
        f"Refund chưa thành công (HTTP {response.status_code}): {response.text[:1000]}",
        status="compensation_required",
    )
    return _get_transaction_snapshot(transaction_id)


async def process_saga(transaction_id: str):
    """Resume a payment Saga. All remote write APIs must stay idempotent by transaction_id."""
    snapshot = _claim_saga(transaction_id)
    if snapshot is None:
        return _get_transaction_snapshot(transaction_id)

    if snapshot["status"] == "compensation_required":
        return await _compensate_debit(snapshot)

    if not snapshot["debit_applied"]:
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                debit_response = await client.post(
                    f"{AUTH_SERVICE_URL}/api/auth/deduct",
                    json={
                        "user_id": snapshot["user_id"],
                        "amount": snapshot["amount"],
                        "transaction_id": transaction_id,
                    },
                    headers=internal_headers(),
                )
        except httpx.RequestError as exc:
            _schedule_saga_retry(transaction_id, f"Auth debit timeout/network error: {exc}")
            return _get_transaction_snapshot(transaction_id)

        if debit_response.status_code != 200:
            message = f"Auth debit failed (HTTP {debit_response.status_code}): {debit_response.text[:1000]}"
            if debit_response.status_code in {400, 404, 409, 422}:
                return _mark_saga_failed(transaction_id, message)
            _schedule_saga_retry(transaction_id, message)
            return _get_transaction_snapshot(transaction_id)

        _update_transaction(transaction_id, debit_applied=True, last_error=None)
        snapshot["debit_applied"] = True

    if not snapshot["tuition_settled"]:
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                tuition_response = await client.post(
                    f"{TUITION_SERVICE_URL}/api/tuitions/{snapshot['mssv']}/pay",
                    json={"transaction_id": transaction_id},
                    headers=internal_headers(),
                )
        except httpx.RequestError as exc:
            _schedule_saga_retry(transaction_id, f"Tuition settlement timeout/network error: {exc}")
            return _get_transaction_snapshot(transaction_id)

        if tuition_response.status_code == 200:
            _update_transaction(transaction_id, tuition_settled=True, last_error=None)
            snapshot["tuition_settled"] = True
        elif tuition_response.status_code >= 500 or tuition_response.status_code in {401, 403, 429}:
            _schedule_saga_retry(
                transaction_id,
                f"Tuition temporary error (HTTP {tuition_response.status_code}): {tuition_response.text[:1000]}",
            )
            return _get_transaction_snapshot(transaction_id)
        else:
            reason = f"Tuition settlement rejected (HTTP {tuition_response.status_code}): {tuition_response.text[:1000]}"
            _mark_compensation_required(transaction_id, reason)
            refreshed = _get_transaction_snapshot(transaction_id)
            if refreshed:
                # Persist compensation_required before calling Auth refund.
                refreshed["debit_applied"] = True
                return await _compensate_debit(refreshed)
            return None

    return _mark_saga_success(transaction_id)


def list_recoverable_sagas(limit: int = 50):
    now = datetime.utcnow()
    with SessionLocal() as db:
        rows = (
            db.query(PaymentTransaction.id)
            .filter(
                PaymentTransaction.status.in_(["processing", "compensation_required"]),
                or_(PaymentTransaction.next_retry_at.is_(None), PaymentTransaction.next_retry_at <= now),
                or_(PaymentTransaction.saga_lease_until.is_(None), PaymentTransaction.saga_lease_until <= now),
            )
            .order_by(PaymentTransaction.created_at.asc())
            .limit(limit)
            .all()
        )
        return [row[0] for row in rows]


async def process_outbox_once():
    now = datetime.utcnow()
    with SessionLocal() as db:
        event = (
            db.query(OutboxEvent)
            .filter(
                OutboxEvent.status.in_(["pending", "processing"]),
                OutboxEvent.next_attempt_at <= now,
                or_(OutboxEvent.locked_until.is_(None), OutboxEvent.locked_until <= now),
            )
            .order_by(OutboxEvent.created_at.asc())
            .with_for_update(skip_locked=True)
            .first()
        )
        if not event:
            return False
        event.status = "processing"
        event.locked_until = now + timedelta(seconds=OUTBOX_LEASE_SECONDS)
        event.attempts = int(event.attempts or 0) + 1
        event_id = event.id
        event_type = event.event_type
        payload = dict(event.payload)
        attempt_number = event.attempts
        db.commit()

    try:
        if event_type != "payment.receipt":
            raise RuntimeError(f"Unsupported outbox event type: {event_type}")
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{NOTIFICATION_SERVICE_URL}/api/notifications/send-receipt",
                json=payload,
                headers={**internal_headers(), "X-Event-ID": event_id},
            )
            response.raise_for_status()
    except Exception as exc:
        retry_delay = min(900, 2 ** min(10, attempt_number))
        with SessionLocal() as db:
            current = db.query(OutboxEvent).filter(OutboxEvent.id == event_id).with_for_update().first()
            if current:
                current.status = "pending"
                current.locked_until = None
                current.next_attempt_at = datetime.utcnow() + timedelta(seconds=retry_delay)
                current.last_error = str(exc)[:2000]
                db.commit()
        logger.warning("Outbox delivery failed event_id=%s retry_in=%ss error=%s", event_id, retry_delay, exc)
        return True

    with SessionLocal() as db:
        current = db.query(OutboxEvent).filter(OutboxEvent.id == event_id).with_for_update().first()
        if current:
            current.status = "sent"
            current.sent_at = datetime.utcnow()
            current.locked_until = None
            current.last_error = None
            db.commit()
    logger.info("Outbox event delivered event_id=%s type=%s", event_id, event_type)
    return True


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
            tuition_res = await client.get(f"{TUITION_SERVICE_URL}/api/tuitions/{payload.mssv}", headers=outbound_headers())
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

    existing = (
        db.query(PaymentTransaction)
        .filter(
            PaymentTransaction.user_id == str(user_data["id"]),
            PaymentTransaction.mssv == payload.mssv,
            PaymentTransaction.status.in_(["pending", "processing", "compensation_required"]),
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
        debit_applied=False,
        tuition_settled=False,
        saga_attempts=0,
    )
    db.add(txn)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Bạn đang có giao dịch chờ xử lý cho MSSV này.") from exc

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
        txn.last_error = "OTP delivery failed during initialization."
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
        raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch.")

    if txn.status == "success":
        return {"success": True, "message": "Giao dịch đã hoàn tất trước đó.", "transaction": transaction_result(txn)}
    if txn.status in {"failed", "otp_locked", "expired"}:
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
        txn.last_error = None
        txn.next_retry_at = None
        db.commit()
    elif txn.status not in {"processing", "compensation_required"}:
        raise HTTPException(status_code=409, detail="Trạng thái giao dịch không hợp lệ.")

    result = await process_saga(txn.id)
    if result and result.get("status") == "success":
        with SessionLocal() as result_db:
            completed = result_db.query(PaymentTransaction).filter(PaymentTransaction.id == txn.id).first()
            return {
                "success": True,
                "message": "Thanh toán học phí thành công!",
                "transaction": transaction_result(completed),
            }
    if result and result.get("status") == "failed":
        raise HTTPException(status_code=409, detail=result.get("last_error") or "Giao dịch thất bại.")
    if result and result.get("status") == "compensation_required":
        raise HTTPException(status_code=503, detail="Đang hoàn tiền bù trừ. Hệ thống sẽ tự động tiếp tục đối soát.")
    raise HTTPException(status_code=503, detail="Giao dịch đang được xử lý hoặc chờ retry. Vui lòng kiểm tra lại sau.")


@router.post("/retry/{transaction_id}")
async def retry_payment_saga(
    transaction_id: str,
    authorization: str = Header(...),
):
    user_data = await get_user_data(authorization)
    snapshot = _get_transaction_snapshot(transaction_id)
    if not snapshot or snapshot["user_id"] != str(user_data["id"]):
        raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch.")
    if snapshot["status"] == "success":
        return {"success": True, "transaction": snapshot}
    if snapshot["status"] not in {"processing", "compensation_required"}:
        raise HTTPException(status_code=409, detail=f"Không thể retry giao dịch ở trạng thái {snapshot['status']}.")

    result = await process_saga(transaction_id)
    if result and result.get("status") == "success":
        return {"success": True, "transaction": result}
    return {"success": False, "transaction": result, "message": "Giao dịch vẫn đang được xử lý; worker sẽ tự động retry."}


@router.get("/status/{transaction_id}")
async def get_payment_status(
    transaction_id: str,
    authorization: str = Header(...),
    db: Session = Depends(get_db),
):
    """Read-only status endpoint used by the OTP page while the Saga is recovering."""
    user_data = await get_user_data(authorization)
    txn = (
        db.query(PaymentTransaction)
        .filter(
            PaymentTransaction.id == transaction_id,
            PaymentTransaction.user_id == str(user_data["id"]),
        )
        .first()
    )
    if not txn:
        raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch.")
    return {"success": True, "transaction": transaction_result(txn)}


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
