from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import SendOtpRequest, SendReceiptRequest
from app.services.email_service import send_otp_email, send_receipt_email

app = FastAPI(title="Notification Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/notifications/send-otp")
async def send_otp_api(payload: SendOtpRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(send_otp_email, payload.email, payload.otp, payload.expires_in_minutes)
    return {"success": True, "message": "Yêu cầu gửi OTP đã được ghi nhận."}

@app.post("/api/notifications/send-receipt")
async def send_receipt_api(payload: SendReceiptRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(send_receipt_email, payload.email, payload.dict())
    return {"success": True, "message": "Yêu cầu gửi biên lai đã được ghi nhận."}

@app.get("/health")
def health():
    return {"status": "ok", "service": "notification-service"}