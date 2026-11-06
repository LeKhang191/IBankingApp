from decimal import Decimal
import hmac
import os

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, WalletOperation
from app.schemas import LoginRequest, TokenResponse, UserOut
from app.security import create_access_token, get_current_user, verify_password
from app.crud import get_user_by_username

router = APIRouter(prefix="/api/auth", tags=["auth"])


class WalletOperationRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    transaction_id: str = Field(min_length=8, max_length=64)


def require_internal_service(x_internal_token: str = Header(default="")):
    expected = os.getenv("INTERNAL_SERVICE_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Internal service token chưa được cấu hình.")
    if not hmac.compare_digest(x_internal_token, expected):
        raise HTTPException(status_code=401, detail="Service authentication failed.")


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
    # JWT hiện tại là stateless. Client xóa token khi logout.
    return {"success": True}


@router.post("/deduct")
def deduct_balance(
    payload: WalletOperationRequest,
    _: None = Depends(require_internal_service),
    db: Session = Depends(get_db),
):
    """Debit idempotent: cùng transaction_id chỉ được trừ đúng một lần."""
    user = (
        db.query(User)
        .filter(User.id == payload.user_id)
        .with_for_update()
        .first()
    )
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")

    existing = (
        db.query(WalletOperation)
        .filter(
            WalletOperation.transaction_id == payload.transaction_id,
            WalletOperation.operation == "DEBIT",
        )
        .first()
    )
    if existing:
        if existing.user_id != payload.user_id or existing.amount != payload.amount:
            raise HTTPException(status_code=409, detail="Transaction ID đã được sử dụng cho thao tác khác.")
        refunded = (
            db.query(WalletOperation)
            .filter(
                WalletOperation.transaction_id == payload.transaction_id,
                WalletOperation.operation == "REFUND",
            )
            .first()
        )
        if refunded:
            raise HTTPException(status_code=409, detail="Giao dịch đã được hoàn tiền, không thể debit lại.")
        return {"success": True, "already_applied": True, "remaining_balance": str(user.balance)}

    if user.balance < payload.amount:
        raise HTTPException(status_code=400, detail="Số dư khả dụng không đủ để thực hiện giao dịch.")

    user.balance -= payload.amount
    db.add(WalletOperation(
        transaction_id=payload.transaction_id,
        operation="DEBIT",
        user_id=user.id,
        amount=payload.amount,
    ))
    db.commit()
    db.refresh(user)
    return {"success": True, "already_applied": False, "remaining_balance": str(user.balance)}


@router.post("/refund")
def refund_balance(
    payload: WalletOperationRequest,
    _: None = Depends(require_internal_service),
    db: Session = Depends(get_db),
):
    """Refund idempotent và chỉ hoàn tiền nếu debit cùng transaction đã tồn tại."""
    user = (
        db.query(User)
        .filter(User.id == payload.user_id)
        .with_for_update()
        .first()
    )
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")

    debit = (
        db.query(WalletOperation)
        .filter(
            WalletOperation.transaction_id == payload.transaction_id,
            WalletOperation.operation == "DEBIT",
        )
        .first()
    )
    if debit is None or debit.user_id != payload.user_id or debit.amount != payload.amount:
        raise HTTPException(status_code=409, detail="Không tìm thấy khoản trừ tiền tương ứng để hoàn.")

    existing_refund = (
        db.query(WalletOperation)
        .filter(
            WalletOperation.transaction_id == payload.transaction_id,
            WalletOperation.operation == "REFUND",
        )
        .first()
    )
    if existing_refund:
        if existing_refund.user_id != payload.user_id or existing_refund.amount != payload.amount:
            raise HTTPException(status_code=409, detail="Thông tin hoàn tiền không khớp.")
        return {"success": True, "already_applied": True, "balance": str(user.balance)}

    user.balance += payload.amount
    db.add(WalletOperation(
        transaction_id=payload.transaction_id,
        operation="REFUND",
        user_id=user.id,
        amount=payload.amount,
    ))
    db.commit()
    db.refresh(user)
    return {"success": True, "already_applied": False, "balance": str(user.balance)}
