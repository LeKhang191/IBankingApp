import hmac
import os

from fastapi import FastAPI, Header, HTTPException, Depends

from app.schemas import SendOtpRequest, SendReceiptRequest
from app.services.email_service import send_otp_email, send_receipt_email

app = FastAPI(title="Notification Service", version="2.0.0")


def require_internal_service(x_internal_token: str = Header(default="")):
    expected = os.getenv("INTERNAL_SERVICE_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Internal service token chưa được cấu hình.")
    if not hmac.compare_digest(x_internal_token, expected):
        raise HTTPException(status_code=401, detail="Service authentication failed.")


@app.post("/api/notifications/send-otp")
async def send_otp_api(
    payload: SendOtpRequest,
    _: None = Depends(require_internal_service),
):
    try:
        await send_otp_email(payload.email, payload.otp, payload.expires_in_minutes)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Notification Service không gửi được email OTP.") from exc
    return {"success": True, "message": "Email OTP đã được gửi."}


@app.post("/api/notifications/send-receipt")
async def send_receipt_api(
    payload: SendReceiptRequest,
    _: None = Depends(require_internal_service),
):
    try:
        await send_receipt_email(payload.email, payload.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Không gửi được email biên lai.") from exc
    return {"success": True, "message": "Email biên lai đã được gửi."}


@app.get("/health")
def health():
    return {"status": "ok", "service": "notification-service"}
