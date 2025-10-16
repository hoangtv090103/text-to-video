"""Admin-related schemas"""
from pydantic import BaseModel, Field


class LLMConfigUpdate(BaseModel):
    """Schema for updating LLM configuration"""
    provider: str = Field(..., description="LLM provider (openai, google, anthropic, etc.)")
    base_url: str | None = Field(None, description="Base URL for the LLM API")
    api_key: str | None = Field(None, description="API key for authentication")
    model: str | None = Field(None, description="Model name to use")


class LLMConfigResponse(BaseModel):
    """Schema for LLM configuration response"""
    provider: str
    base_url: str | None = None
    has_api_key: bool = False  # Don't expose actual key
    model: str | None = None


class FetchModelsRequest(BaseModel):
    """Schema for fetching available models"""
    provider: str
    base_url: str | None = None
    api_key: str | None = None


class ModelInfo(BaseModel):
    """Information about a model"""
    id: str
    name: str
    description: str | None = None


class FetchModelsResponse(BaseModel):
    """Schema for models list response"""
    success: bool
    models: list[ModelInfo] = []
    error: str | None = None


class TestModelRequest(BaseModel):
    """Schema for testing a model"""
    provider: str
    base_url: str | None = None
    api_key: str | None = None
    model: str


class TestModelResponse(BaseModel):
    """Schema for model test response"""
    success: bool
    message: str
    response: str | None = None
    latency_ms: float | None = None
