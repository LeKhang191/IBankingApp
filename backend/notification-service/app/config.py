from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "iBanking <noreply@ibanking.local>"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
