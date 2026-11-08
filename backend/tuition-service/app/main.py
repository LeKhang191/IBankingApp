from decimal import Decimal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.routers import tuition
from app.models import Tuition

app = FastAPI(title="Tuition Service", version="2.0.0")

from app.observability import install_request_logging
install_request_logging(app, "tuition-service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Internal-Token"],
)

app.include_router(tuition.router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if settings.SEED_DEMO_DATA:
            # Corresponding demo identities: sv001, sv002, sv003.
            # A payer may enter any of these codes to pay on behalf of another student.
            demo_tuitions = (
                ("52000001", "Nguyễn Văn An", Decimal("15000000.00")),
                ("52000002", "Trần Thị Bích", Decimal("12500000.00")),
                ("52000003", "Lê Hoàng Cường", Decimal("10000000.00")),
            )
            for student_code, student_name, fee in demo_tuitions:
                existing = db.query(Tuition).filter(Tuition.student_code == student_code).first()
                if existing is None:
                    db.add(Tuition(
                        student_code=student_code,
                        student_name=student_name,
                        tuition_fee=fee,
                        is_paid=False,
                    ))
                elif (student_code == "52000002" and existing.is_paid
                      and existing.paid_transaction_id is None and existing.paid_at is None):
                    # Old source seeded sv002's tuition as paid without a transaction.
                    # Restore this untouched demo fixture so sv001 can pay on behalf.
                    existing.is_paid = False
            db.commit()
        # Never reset a tuition that has an actual payment transaction.
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "service": "tuition-service"}
