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
    ML_SERVICE_TIMEOUT: int = 30
    LOG_LEVEL: str = "INFO"
    IDEMPOTENCY_RESPONSE_TTL_SECONDS: int = 24 * 60 * 60
    IDEMPOTENCY_LOCK_TTL_SECONDS: int = 30
    IDEMPOTENCY_WAIT_TIMEOUT_SECONDS: float = 5.0
    IDEMPOTENCY_WAIT_INTERVAL_SECONDS: float = 0.1
    FSRS_DESIRED_RETENTION: float = 0.9
    FSRS_OPTIMIZER_MIN_REVIEWS: int = 50
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_ML_REQUEST_TOPIC: str = "ml.cards.generate.request"
    KAFKA_ML_RESPONSE_TOPIC: str = "ml.cards.generate.response"
    KAFKA_ML_CONSUMER_GROUP: str = "sigmacards-ml-client"

    class Config:
        env_file = ".env"

settings = Settings() 