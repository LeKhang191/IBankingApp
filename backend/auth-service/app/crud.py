from sqlalchemy.orm import Session

from app.models import User
from app.security import hash_password


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def seed_demo_users(db: Session) -> None:
    """Tạo sẵn 2 tài khoản demo giống mockApi.js nếu DB chưa có ai."""
    if db.query(User).first() is not None:
        return

    demo_users = [
        User(
            id="u1",
            username="sv001",
            hashed_password=hash_password("123456"),
            name="Nguyễn Văn An",
            phone="0901234567",
            email="an.nguyen@student.tdtu.edu.vn",
            balance=12_000_000,
        ),
        User(
            id="u2",
            username="sv002",
            hashed_password=hash_password("123456"),
            name="Trần Thị Bích",
            phone="0912345678",
            email="bich.tran@student.tdtu.edu.vn",
            balance=3_000_000,
        ),
    ]
    db.add_all(demo_users)
    db.commit()