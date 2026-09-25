from decimal import Decimal
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserOut
from app.security import create_access_token, get_current_user, verify_password
from app.crud import get_user_by_username

router = APIRouter(prefix="/api/auth", tags=["auth"])


class DeductRequest(BaseModel):
    amount: Decimal


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_username(db, payload.username)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Sai tên đăng nhập hoặc mật khẩu.")

    token = create_access_token(user.id)
    return TokenResponse(token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    return {"success": True}


@router.post("/deduct")
def deduct_balance(payload: DeductRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user.id).with_for_update().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin người dùng.")

    if user.balance < payload.amount:
        raise HTTPException(status_code=400, detail="Số dư không đủ để thực hiện giao dịch.")
    
    user.balance -= payload.amount
    db.commit()
    db.refresh(user)
    
    return {"success": True, "new_balance": float(user.balance)}