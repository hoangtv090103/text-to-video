from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    LOG_LEVEL: str = "INFO"
    TTS_SERVICE_URL: str
    LLM_URL: str
    LLM_API_KEY: str
    LLM_MODEL: str
    PRESENTON_BASE_URL: str

    class Config:
        env_file = "/Users/hoangtv/text-to-video/server/.env"
        env_file_encoding = "utf-8"


settings = Settings()
