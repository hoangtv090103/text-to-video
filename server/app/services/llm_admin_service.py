"""Admin service for LLM configuration management"""

import time
import httpx
from typing import Any
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from app.core.config import settings
from app.schemas.admin import ModelInfo, FetchModelsResponse, TestModelResponse


class LLMAdminService:
    """Service for managing LLM configuration"""

    @staticmethod
    async def fetch_models(
        provider: str, base_url: str | None = None, api_key: str | None = None
    ) -> FetchModelsResponse:
        """Fetch available models from provider"""
        try:
            if provider == "openai":
                return await LLMAdminService._fetch_openai_models(base_url, api_key)
            elif provider == "google":
                return await LLMAdminService._fetch_google_models()
            elif provider == "anthropic":
                return await LLMAdminService._fetch_anthropic_models()
            elif provider == "local":
                return FetchModelsResponse(
                    success=True,
                    models=[
                        ModelInfo(
                            id="local", name="Local Model", description="Locally hosted model"
                        )
                    ],
                )
            else:
                return FetchModelsResponse(
                    success=False, error=f"Provider '{provider}' not supported for model listing"
                )
        except Exception as e:
            return FetchModelsResponse(success=False, error=f"Failed to fetch models: {str(e)}")

    @staticmethod
    async def _fetch_openai_models(
        base_url: str | None, api_key: str | None
    ) -> FetchModelsResponse:
        """Fetch OpenAI-compatible models"""
        url = base_url or "https://api.openai.com/v1"
        key = api_key or settings.OPENAI_API_KEY

        if not key:
            return FetchModelsResponse(success=False, error="API key is required for OpenAI")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{url}/models", headers={"Authorization": f"Bearer {key}"}, timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

                models = []
                for model in data.get("data", []):
                    model_id = model.get("id", "")
                    # Filter to common chat models
                    # if any(x in model_id for x in ["gpt", "chatgpt", "turbo", "o1", "o3"]):
                    models.append(
                        ModelInfo(
                            id=model_id, name=model_id, description=f"OpenAI model: {model_id}"
                        )
                    )

                return FetchModelsResponse(success=True, models=models)
        except Exception as e:
            return FetchModelsResponse(
                success=False, error=f"Failed to fetch OpenAI models: {str(e)}"
            )

    @staticmethod
    async def _fetch_google_models() -> FetchModelsResponse:
        """Fetch Google Gemini models"""
        models = [
            ModelInfo(id="gemini-pro", name="Gemini Pro", description="Google Gemini Pro model"),
            ModelInfo(
                id="gemini-1.5-pro",
                name="Gemini 1.5 Pro",
                description="Google Gemini 1.5 Pro model",
            ),
            ModelInfo(
                id="gemini-1.5-flash",
                name="Gemini 1.5 Flash",
                description="Google Gemini 1.5 Flash model",
            ),
        ]
        return FetchModelsResponse(success=True, models=models)

    @staticmethod
    async def _fetch_anthropic_models() -> FetchModelsResponse:
        """Fetch Anthropic Claude models"""
        models = [
            ModelInfo(
                id="claude-3-opus-20240229",
                name="Claude 3 Opus",
                description="Most capable Claude 3 model",
            ),
            ModelInfo(
                id="claude-3-sonnet-20240229",
                name="Claude 3 Sonnet",
                description="Balanced Claude 3 model",
            ),
            ModelInfo(
                id="claude-3-haiku-20240307",
                name="Claude 3 Haiku",
                description="Fastest Claude 3 model",
            ),
            ModelInfo(
                id="claude-3-5-sonnet-20241022",
                name="Claude 3.5 Sonnet",
                description="Latest Claude 3.5 model",
            ),
        ]
        return FetchModelsResponse(success=True, models=models)

    @staticmethod
    async def test_model(
        provider: str, model: str, base_url: str | None = None, api_key: str | None = None
    ) -> TestModelResponse:
        """Test if a model is working"""
        start_time = time.time()

        try:
            if provider == "openai":
                llm = ChatOpenAI(
                    model=model,
                    api_key=api_key or settings.OPENAI_API_KEY,
                    base_url=base_url or settings.OPENAI_BASE_URL or None,
                    temperature=0.7,
                )
            elif provider == "google":
                llm = ChatGoogleGenerativeAI(
                    model=model, google_api_key=api_key or settings.GOOGLE_API_KEY, temperature=0.7
                )
            elif provider == "anthropic":
                llm = ChatAnthropic(
                    model=model, api_key=api_key or settings.ANTHROPIC_API_KEY, temperature=0.7
                )
            else:
                return TestModelResponse(
                    success=False, message=f"Provider '{provider}' not supported for testing"
                )

            # Test with a simple message
            messages = [HumanMessage(content="Say 'Hello' in one word.")]
            response = await llm.ainvoke(messages)

            latency = (time.time() - start_time) * 1000  # Convert to ms

            return TestModelResponse(
                success=True,
                message="Model test successful",
                response=response.content,
                latency_ms=round(latency, 2),
            )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return TestModelResponse(
                success=False, message=f"Model test failed: {str(e)}", latency_ms=round(latency, 2)
            )

    @staticmethod
    def get_current_config() -> dict[str, Any]:
        """Get current LLM configuration"""
        return {
            "provider": settings.LLM_PROVIDER,
            "base_url": settings.OPENAI_BASE_URL if settings.LLM_PROVIDER == "openai" else None,
            "has_api_key": bool(
                settings.OPENAI_API_KEY
                if settings.LLM_PROVIDER == "openai"
                else (
                    settings.GOOGLE_API_KEY
                    if settings.LLM_PROVIDER == "google"
                    else (
                        settings.ANTHROPIC_API_KEY if settings.LLM_PROVIDER == "anthropic" else None
                    )
                )
            ),
            "model": (
                settings.OPENAI_MODEL
                if settings.LLM_PROVIDER == "openai"
                else (
                    settings.GOOGLE_MODEL
                    if settings.LLM_PROVIDER == "google"
                    else settings.ANTHROPIC_MODEL if settings.LLM_PROVIDER == "anthropic" else None
                )
            ),
        }

    @staticmethod
    def update_config(
        provider: str, base_url: str | None, api_key: str | None, model: str | None
    ) -> dict[str, Any]:
        """Update LLM configuration (in-memory only)"""
        settings.LLM_PROVIDER = provider

        if provider == "openai":
            if base_url:
                settings.OPENAI_BASE_URL = base_url
            if api_key:
                settings.OPENAI_API_KEY = api_key
            if model:
                settings.OPENAI_MODEL = model
        elif provider == "google":
            if api_key:
                settings.GOOGLE_API_KEY = api_key
            if model:
                settings.GOOGLE_MODEL = model
        elif provider == "anthropic":
            if api_key:
                settings.ANTHROPIC_API_KEY = api_key
            if model:
                settings.ANTHROPIC_MODEL = model

        return LLMAdminService.get_current_config()
