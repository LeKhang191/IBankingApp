from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Tuition
from app.schemas import TuitionOut, TuitionMessage

router = APIRouter(prefix="/api/tuitions", tags=["tuitions"])

@router.get("/{student_code}", response_model=TuitionOut)
def get_tuition(student_code: str, db: Session = Depends(get_db)):
    tuition = db.query(Tuition).filter(Tuition.student_code == student_code).first()
    if not tuition:
        raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên với MSSV này.")
    return tuition

@router.post("/{mssv}/pay")
def pay_tuition(mssv: str, db: Session = Depends(get_db)):
    tuition = db.query(Tuition).filter(Tuition.student_code == mssv).with_for_update().first()
    
    if not tuition:
        raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên.")
    
    if tuition.is_paid:
        raise HTTPException(status_code=400, detail="Khoản học phí này đã được thanh toán.")
    
    tuition.is_paid = True
    tuition.paid_at = datetime.utcnow()
    db.commit()
    db.refresh(tuition)
    return {"success": True, "message": "Gạch nợ học phí thành công."}