from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://tuition_user:change_me@postgres:5432/tuition_db"
    CORS_ALLOW_ORIGINS: str = "http://localhost:5173"
    SEED_DEMO_DATA: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
