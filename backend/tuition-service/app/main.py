from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.routers import tuition
from app.models import Tuition

app = FastAPI(title="Tuition Service", version="2.0.0")

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
        if db.query(Tuition).count() == 0:
            db.add_all([
                Tuition(student_code="52000001", student_name="Nguyễn Văn A", tuition_fee=15000000, is_paid=False),
                Tuition(student_code="52000002", student_name="Trần Thị B", tuition_fee=12500000, is_paid=True),
            ])
            db.commit()
        # Không tự reset trạng thái học phí khi service restart.
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "service": "tuition-service"}
