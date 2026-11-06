from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@postgres:5432/ibanking"
    JWT_SECRET_KEY: str = "change_this_to_a_long_random_secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    CORS_ALLOW_ORIGINS: str = "http://localhost:5173"

    # Root .env may contain variables belonging to other services; ignore those.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
