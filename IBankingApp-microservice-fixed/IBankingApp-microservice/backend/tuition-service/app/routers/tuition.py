import hmac
import os
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Tuition
from app.schemas import TuitionOut

router = APIRouter(prefix="/api/tuitions", tags=["tuitions"])


class MarkPaidRequest(BaseModel):
    transaction_id: str = Field(min_length=8, max_length=64)


def require_internal_service(x_internal_token: str = Header(default="")):
    expected = os.getenv("INTERNAL_SERVICE_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Internal service token chưa được cấu hình.")
    if not hmac.compare_digest(x_internal_token, expected):
        raise HTTPException(status_code=401, detail="Service authentication failed.")


@router.get("/{student_code}", response_model=TuitionOut)
def get_tuition(student_code: str, db: Session = Depends(get_db)):
    tuition = db.query(Tuition).filter(Tuition.student_code == student_code).first()
    if not tuition:
        raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên với MSSV này.")
    return tuition


@router.post("/{mssv}/pay")
def pay_tuition(
    mssv: str,
    payload: MarkPaidRequest,
    _: None = Depends(require_internal_service),
    db: Session = Depends(get_db),
):
    """Idempotent settlement với row lock, chống hai tài khoản gạch nợ cùng MSSV."""
    tuition = (
        db.query(Tuition)
        .filter(Tuition.student_code == mssv)
        .with_for_update()
        .first()
    )
    if not tuition:
        raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên.")

    if tuition.is_paid:
        if tuition.paid_transaction_id == payload.transaction_id:
            return {"success": True, "already_applied": True, "message": "Khoản học phí đã được ghi nhận cho giao dịch này."}
        raise HTTPException(status_code=409, detail="Khoản học phí này đã được thanh toán bởi giao dịch khác.")

    tuition.is_paid = True
    tuition.paid_at = datetime.utcnow()
    tuition.paid_transaction_id = payload.transaction_id
    db.commit()
    db.refresh(tuition)
    return {"success": True, "already_applied": False, "message": "Gạch nợ học phí thành công."}
