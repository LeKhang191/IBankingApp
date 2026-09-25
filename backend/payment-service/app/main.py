import httpx
from fastapi import FastAPI, APIRouter, HTTPException, Header
from pydantic import BaseModel

app = FastAPI(title="Payment Service")
router = APIRouter(prefix="/api/payments", tags=["payments"])

AUTH_SERVICE_URL = "http://auth-service:8000"
TUITION_SERVICE_URL = "http://tuition-service:8002"

class PaymentRequest(BaseModel):
    mssv: str

@router.post("/tuition")
async def process_tuition_payment(payload: PaymentRequest, authorization: str = Header(...)):
    async with httpx.AsyncClient() as client:
        tuition_res = await client.get(f"{TUITION_SERVICE_URL}/api/tuitions/{payload.mssv}")
        if tuition_res.status_code != 200:
            raise HTTPException(status_code=tuition_res.status_code, detail="Không lấy được thông tin học phí.")
        
        tuition_data = tuition_res.json()
        if tuition_data["is_paid"]:
            raise HTTPException(status_code=400, detail="Học phí này đã được thanh toán.")
        
        amount = tuition_data["amount"] 
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
        
        return {"success": True, "message": "Thanh toán học phí thành công!"}

app.include_router(router)