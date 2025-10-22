from typing import Any, Dict

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
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_DB: int = Field(default=0, description="Redis DB index")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # Core service URLs and models
    TTS_SERVICE_URL: str = Field(default="http://localhost:4123/v1/audio/speech", description="TTS service URL")
    LLM_URL: str = Field(default="", description="LLM service URL (optional)")
    LLM_API_KEY: str = Field(default="", description="LLM API key")
    LLM_MODEL: str = Field(default="qwen3:4b", description="Default LLM model")

    # LLM Provider Configuration
    LLM_PROVIDER: str = Field(default="openai", description="LLM provider")
    LLM_CONFIG: Dict[str, Any] = Field(default_factory=dict, description="LLM provider config")

    # Provider-specific configurations
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="qwen3:4b", description="OpenAI model")
    OPENAI_BASE_URL: str = Field(default="http://localhost:11434/v1", description="OpenAI base URL")

    GOOGLE_API_KEY: str = Field(default="", description="Google API key")
    GOOGLE_MODEL: str = Field(default="gemini-pro", description="Google model")

    ANTHROPIC_API_KEY: str = Field(default="", description="Anthropic API key")
    ANTHROPIC_MODEL: str = Field(default="claude-3-sonnet-20240229", description="Anthropic model")

    HUGGINGFACE_MODEL: str = Field(default="google/flan-t5-base", description="HuggingFace model")
    HUGGINGFACE_API_KEY: str = Field(default="", description="HuggingFace API key")

    LOCAL_MODEL_PATH: str = Field(default="", description="Local model path")
    LOCAL_MODEL_TYPE: str = Field(default="auto", description="Local model type")

    PRESENTON_BASE_URL: str = Field(default="http://localhost:9000", description="Presenton API base URL")

    # Visual quality settings
    IMAGE_DPI: int = Field(default=150, description="DPI for generated images (150 for high quality, 300 for print quality)")
    IMAGE_QUALITY: int = Field(default=95, description="JPEG/PNG quality (0-100)")
    SLIDE_WIDTH: int = Field(default=1920, description="Standard 1080p width")
    SLIDE_HEIGHT: int = Field(default=1080, description="Standard 1080p height (16:9 aspect ratio)")
    CHART_DPI: int = Field(default=150, description="DPI specifically for charts/graphs")
    CODE_DPI: int = Field(default=150, description="DPI specifically for code screenshots")

    # Storage paths - use persistent storage instead of /tmp
    ASSET_STORAGE_PATH: str = Field(default="./data/assets", description="Asset storage path")
    VIDEO_OUTPUT_PATH: str = Field(default="./data/videos", description="Video output path")
    VISUAL_STORAGE_PATH: str = Field(default="./data/visuals", description="Visuals storage path")

    # Concurrency limits
    MAX_CONCURRENT_JOBS: int = Field(default=5, description="Max concurrent jobs")

    # Storage backend configuration
    ASSET_STORAGE_BACKEND: str = Field(default="local", description="Storage backend (local or s3)")
    S3_BUCKET: str = Field(default="", description="S3 bucket name")
    S3_REGION: str = Field(default="us-east-1", description="S3 region")
    S3_ACCESS_KEY: str = Field(default="", description="S3 access key")
    S3_SECRET_KEY: str = Field(default="", description="S3 secret key")

    # Cache TTL settings
    CACHE_LLM_TTL: int = Field(default=3600, description="LLM cache TTL in seconds")
    CACHE_TTS_TTL: int = Field(default=86400, description="TTS cache TTL in seconds")
    CACHE_VISUAL_TTL: int = Field(default=86400, description="Visual cache TTL in seconds")

    # Job and resource limits
    JOB_RETENTION_HOURS: int = Field(default=24, description="Job retention period in hours")
    MAX_UPLOAD_SIZE_MB: int = Field(default=50, description="Maximum upload size in MB")
    MAX_CONCURRENT_SCENES: int = Field(default=10, description="Maximum concurrent scenes")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
print(settings)
