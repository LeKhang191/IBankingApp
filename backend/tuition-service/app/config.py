from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://ibanking:changeme@postgres:5432/auth_db"
    JWT_SECRET_KEY: str = "change_this_to_a_long_random_secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    CORS_ALLOW_ORIGINS: str = "http://localhost:5173"

    class Config:
        env_file = ".env"


settings = Settings()