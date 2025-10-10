from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings


class LLMProvider(str):
    """Supported LLM providers"""

    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"


class Settings(BaseSettings):
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    LOG_LEVEL: str = "INFO"
    # Core service URLs and models
    TTS_SERVICE_URL: str = "http://localhost:4123/v1/audio/speech"
    LLM_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-3.5-turbo"

    # LLM Provider Configuration
    LLM_PROVIDER: str = Field(default="openai")
    LLM_CONFIG: dict[str, Any] = Field(default_factory=dict)

    # Provider-specific configurations
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    OPENAI_BASE_URL: str = ""

    GOOGLE_API_KEY: str = ""
    GOOGLE_MODEL: str = "gemini-pro"

    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-sonnet-20240229"

    HUGGINGFACE_MODEL: str = "google/flan-t5-base"
    HUGGINGFACE_API_KEY: str = ""

    LOCAL_MODEL_PATH: str = ""
    LOCAL_MODEL_TYPE: str = "auto"

    PRESENTON_BASE_URL: str = "http://localhost:5001"

    # Storage paths - use persistent storage instead of /tmp
    ASSET_STORAGE_PATH: str = "./data/assets"
    VIDEO_OUTPUT_PATH: str = "./data/videos"
    VISUAL_STORAGE_PATH: str = "./data/visuals"

    # Concurrency limits
    MAX_CONCURRENT_JOBS: int = 5

    class Config:
        import os
        env_file = os.getenv("APP_ENV_FILE", ".env")
        env_file_encoding = "utf-8"


settings = Settings()
