from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_PASSWORD: str
    REDIS_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    ENV: str = "development"
    ALGORITHM: str = "HS256"
    ML_SERVICE_URL: str
    ML_SERVICE_TIMEOUT: int
    LOG_LEVEL: str = "INFO"
    IDEMPOTENCY_RESPONSE_TTL_SECONDS: int = 24 * 60 * 60
    IDEMPOTENCY_LOCK_TTL_SECONDS: int = 30
    IDEMPOTENCY_WAIT_TIMEOUT_SECONDS: float = 5.0
    IDEMPOTENCY_WAIT_INTERVAL_SECONDS: float = 0.1
    FSRS_DESIRED_RETENTION: float = 0.9
    FSRS_OPTIMIZER_MIN_REVIEWS: int = 50

    class Config:
        env_file = ".env"

settings = Settings() 