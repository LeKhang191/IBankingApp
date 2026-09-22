from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.routers import tuition
from app.models import Tuition

app = FastAPI(title="Tuition Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tuition.router)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        if db.query(Tuition).count() == 0:
            demo_tuitions = [
                Tuition(student_code="52000001", student_name="Nguyễn Văn A", tuition_fee=15000000, is_paid=False),
                Tuition(student_code="52000002", student_name="Trần Thị B", tuition_fee=12500000, is_paid=True),
            ]
            db.add_all(demo_tuitions)
            db.commit()
    finally:
        db.close()

@app.get("/health")
def health():
    return {"status": "ok", "service": "tuition-service"}