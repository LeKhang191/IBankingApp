from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import User, WalletOperation
from app.security import hash_password


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def seed_demo_users(db: Session) -> None:
    """Create the three fixed demo accounts without resetting real payment history.

    sv001: payer with 30 million VND; sv002: pay-on-behalf recipient;
    sv003: payer with an intentionally insufficient balance.
    """
    demo_users = (
        ("u1", "sv001", "Nguyễn Văn An", "0901234567", "an.nguyen@student.tdtu.edu.vn", Decimal("30000000.00")),
        ("u2", "sv002", "Trần Thị Bích", "0912345678", "bich.tran@student.tdtu.edu.vn", Decimal("0.00")),
        ("u3", "sv003", "Lê Hoàng Cường", "0923456789", "cuong.le@student.tdtu.edu.vn", Decimal("1000000.00")),
    )
    for user_id, username, name, phone, email, initial_balance in demo_users:
        existing = get_user_by_username(db, username)
        if existing is None:
            db.add(User(
                id=user_id,
                username=username,
                hashed_password=hash_password("123456"),
                name=name,
                phone=phone,
                email=email,
                balance=initial_balance,
            ))
            continue

        # Upgrade only untouched legacy seed balances (15m and 3m respectively).
        # Never replenish a payer after a real demo payment / refund.
        legacy_balance = {"sv001": Decimal("15000000.00"), "sv002": Decimal("3000000.00")}.get(username)
        if legacy_balance is not None and existing.balance == legacy_balance:
            has_wallet_history = (
                db.query(WalletOperation.id)
                .filter(WalletOperation.user_id == existing.id)
                .first() is not None
            )
            if not has_wallet_history:
                existing.balance = initial_balance

    db.commit()
