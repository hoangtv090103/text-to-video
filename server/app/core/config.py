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
    
    # Storage paths - use persistent storage instead of /tmp
    ASSET_STORAGE_PATH: str = "./data/assets"
    VIDEO_OUTPUT_PATH: str = "./data/videos" 
    VISUAL_STORAGE_PATH: str = "./data/visuals"
    
    # Concurrency limits
    MAX_CONCURRENT_JOBS: int = 5

    class Config:
        env_file = "/Users/hoangtv/text-to-video/server/.env"
        env_file_encoding = "utf-8"


settings = Settings()
