from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "code_reviewer"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Gemini AI
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_DIM: int = 768

    # Обмеження та безпека
    MAX_CODE_CHARS: int = 20000
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    SEMGREP_BIN: str = "semgrep"

    # Відновлення пароля. Без SMTP посилання для скидання пишеться в лог сервера
    APP_URL: str = "http://localhost:5173"  # адреса клієнта, яка потрапляє в посилання з листа
    PASSWORD_RESET_MINUTES: int = 30
    VERIFY_EMAIL_HOURS: int = 24  # скільки діє посилання підтвердження email
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None

    # Вхід через GitHub (OAuth App). Без цих двох значень кнопка входу не показується
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None

    # Вхід через Google (OAuth client типу Web application). Без цих двох значень кнопка не показується
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # App
    APP_ENV: str = "development"
    DEBUG: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"  # невідомі змінні в .env (наприклад, застарілий GITHUB_TOKEN) не ламають запуск


settings = Settings()
