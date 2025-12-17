import os
from typing import List
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class Settings:
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data.db")
    
    # JWT Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your_secret_key_here_change_in_production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "600"))  # 10 часов
    
    # Telegram Bot
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # Google Sheets
    GOOGLE_SHEETS_API_KEY: str = os.getenv("GOOGLE_SHEETS_API_KEY", "")
    GOOGLE_CREDENTIALS_PATH: str = os.getenv("GOOGLE_CREDENTIALS_PATH", "")
    SPREADSHEET_ID_SHAXMATKA_ID: str = os.getenv("SPREADSHEET_ID_SHAXMATKA_ID", "")
    SPREADSHEET_ID_LID_ID: str = os.getenv("SPREADSHEET_ID_LID_ID", "")
    SPREADSHEET_ID_PRICE_ID: str = os.getenv("SPREADSHEET_ID_PRICE_ID", "")
    SPREADSHEET_ID_REESTR_ID: str = os.getenv("SPREADSHEET_ID_REESTR_ID", "")
    
    # Email Settings
    EMAIL_USER: str = os.getenv("EMAIL_USER", "your_email@gmail.com")
    EMAIL_PASS: str = os.getenv("EMAIL_PASS", "your_app_password")
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    
    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    # Instagram Integration (настройки хранятся в БД, админ добавляет через панель)
    # Эти переменные оставлены для обратной совместимости, но не используются
    # INSTAGRAM_APP_ID: str = os.getenv("INSTAGRAM_APP_ID", "")
    # INSTAGRAM_APP_SECRET: str = os.getenv("INSTAGRAM_APP_SECRET", "")
    # INSTAGRAM_REDIRECT_URI: str = os.getenv("INSTAGRAM_REDIRECT_URI", "")

# Создаем экземпляр настроек
settings = Settings()
