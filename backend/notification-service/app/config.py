from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""          
    SMTP_PASSWORD: str = ""      
    EMAIL_FROM: str = "iBanking System <noreply@ibanking.vn>"

    class Config:
        env_file = ".env"

settings = Settings()