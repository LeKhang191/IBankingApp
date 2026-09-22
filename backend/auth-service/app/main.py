from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.routers import auth
from app.crud import seed_demo_users

app = FastAPI(title="Auth Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_demo_users(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "service": "auth-service"}