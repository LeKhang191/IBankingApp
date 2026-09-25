import httpx
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, APIRouter, HTTPException, Header
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Payment Service")
router = APIRouter(prefix="/api/payments", tags=["payments"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AUTH_SERVICE_URL = "http://auth-service:8001"
TUITION_SERVICE_URL = "http://tuition-service:8001"
NOTIFICATION_SERVICE_URL = "http://notification-service:8003"

TRANSACTIONS_DB: List[Dict[str, Any]] = []

class PaymentRequest(BaseModel):
    mssv: str

@router.post("/tuition")
async def process_tuition_payment(payload: PaymentRequest, authorization: str = Header(...)):
    async with httpx.AsyncClient() as client:
        user_email = None
        try:
            user_res = await client.get(
                f"{AUTH_SERVICE_URL}/api/auth/me",
                headers={"Authorization": authorization}
            )
            if user_res.status_code == 200:
                user_email = user_res.json().get("email")
        except Exception as e:
            print(f"Lỗi lấy thông tin người dùng: {e}")

        tuition_res = await client.get(f"{TUITION_SERVICE_URL}/api/tuitions/{payload.mssv}")
        if tuition_res.status_code != 200:
            raise HTTPException(status_code=tuition_res.status_code, detail="Không lấy được thông tin học phí.")
        
        tuition_data = tuition_res.json()
        if tuition_data.get("is_paid"):
            raise HTTPException(status_code=400, detail="Học phí này đã được thanh toán.")
        
        amount = tuition_data.get("tuition_fee") or tuition_data.get("amount")
        if amount is None:
            raise HTTPException(status_code=500, detail="Không xác định được số tiền học phí.")

        deduct_res = await client.post(
            f"{AUTH_SERVICE_URL}/api/auth/deduct",
            json={"amount": amount},
            headers={"Authorization": authorization}
        )
        if deduct_res.status_code != 200:
            error_detail = deduct_res.json().get("detail", "Thanh toán thất bại do lỗi số dư.")
            raise HTTPException(status_code=deduct_res.status_code, detail=error_detail)

        pay_res = await client.post(
            f"{TUITION_SERVICE_URL}/api/tuitions/{payload.mssv}/pay"
        )
        if pay_res.status_code != 200:
            raise HTTPException(status_code=500, detail="Trừ tiền thành công nhưng gạch nợ hệ thống thất bại.")
        
        created_at_dt = datetime.now()
        txn_id = f"TXN{int(created_at_dt.timestamp() * 1000)}"
        student_name = tuition_data.get("student_name", "Sinh viên")

        txn_record = {
            "id": txn_id,
            "mssv": payload.mssv,
            "studentName": student_name,
            "amount": amount,
            "createdAt": created_at_dt.isoformat(),
            "status": "success"
        }
        TRANSACTIONS_DB.insert(0, txn_record)

        if user_email:
            receipt_payload = {
                "email": user_email,
                "transaction_id": txn_id,
                "student_code": payload.mssv,
                "student_name": student_name,
                "amount": float(amount),
                "created_at": created_at_dt.strftime("%Y-%m-%d %H:%M:%S")
            }
            try:
                await client.post(
                    f"{NOTIFICATION_SERVICE_URL}/api/notifications/send-receipt",
                    json=receipt_payload,
                    timeout=5.0
                )
            except Exception as notify_err:
                print(f"[Warning] Gửi thông báo biên lai thất bại: {notify_err}")
        
        return {"success": True, "message": "Thanh toán học phí thành công!", "transaction": txn_record}

@router.get("/history")
async def get_payment_history():
    return TRANSACTIONS_DB

app.include_router(router)