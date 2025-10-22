import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from app.core.config import LLMProvider, settings

logger = logging.getLogger(__name__)


class ModelCacheManager:
    """Cache manager for LLM model information to avoid repeated API calls"""

    def __init__(self, cache_duration_hours: int = 24):
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()

    async def get_models(self, provider: str) -> List[str]:
        """Get cached models for a provider, fetch if not cached or expired"""
        async with self._lock:
            cache_key = f"models_{provider}"

            # Check if cache exists and is not expired
            if (
                cache_key in self._cache
                and cache_key in self._cache_timestamps
                and datetime.now() - self._cache_timestamps[cache_key] < self.cache_duration
            ):
                logger.debug(f"Using cached models for {provider}")
                return self._cache[cache_key]["models"]

            # Cache miss or expired, fetch fresh data
            logger.info(f"Fetching fresh models for {provider}")
            models = await self._fetch_models_from_provider(provider)

            # Cache the result
            self._cache[cache_key] = {
                "models": models,
                "fetched_at": datetime.now().isoformat(),
                "provider": provider,
            }
            self._cache_timestamps[cache_key] = datetime.now()

            logger.info(f"Cached {len(models)} models for {provider}")
            return models

    async def _fetch_models_from_provider(self, provider: str) -> List[str]:
        """Fetch models from the provider's API"""
        try:
            if provider == LLMProvider.OPENAI:
                return await self._fetch_openai_models()
            if provider == LLMProvider.GOOGLE:
                return await self._fetch_google_models()
            if provider == LLMProvider.ANTHROPIC:
                return await self._fetch_anthropic_models()
            if provider == LLMProvider.HUGGINGFACE:
                return await self._fetch_huggingface_models()
            if provider == LLMProvider.LOCAL:
                return await self._fetch_local_models()
            logger.warning(f"Unknown provider for model fetching: {provider}")
            return []

        except Exception as e:
            logger.error(f"Failed to fetch models for {provider}", extra={"error": str(e)})
            # Return fallback models
            return self._get_fallback_models(provider)

    async def _fetch_openai_models(self) -> List[str]:
        """Fetch available models from OpenAI API"""
        try:
            import httpx

            api_key = settings.OPENAI_API_KEY or settings.LLM_API_KEY
            if not api_key:
                return ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )

                if response.status_code == 200:
                    data = response.json()
                    models = []
                    for model in data.get("data", []):
                        model_id = model.get("id", "")
                        # Filter for chat models
                        if any(x in model_id for x in ["gpt-3.5", "gpt-4"]):
                            models.append(model_id)

                    # Sort by preference
                    preferred_order = ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
                    sorted_models = []
                    for pref in preferred_order:
                        matching = [m for m in models if pref in m]
                        sorted_models.extend(sorted(matching, reverse=True))

                    return sorted_models or models
                logger.warning(f"OpenAI API returned {response.status_code}")
                return ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]

        except Exception as e:
            logger.error("Failed to fetch OpenAI models", extra={"error": str(e)})
            return ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]

    async def _fetch_google_models(self) -> List[str]:
        """Fetch available models from Google AI API"""
        try:
            import httpx

            api_key = settings.GOOGLE_API_KEY
            if not api_key:
                return ["gemini-pro", "gemini-1.5-flash", "gemini-1.5-pro"]

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                )

                if response.status_code == 200:
                    data = response.json()
                    models = []
                    for model in data.get("models", []):
                        model_name = model.get("name", "").split("/")[-1]
                        if model_name and not model_name.startswith("tuned"):
                            models.append(model_name)

                    return (
                        sorted(models)
                        if models
                        else ["gemini-pro", "gemini-1.5-flash", "gemini-1.5-pro"]
                    )
                logger.warning(f"Google AI API returned {response.status_code}")
                return ["gemini-pro", "gemini-1.5-flash", "gemini-1.5-pro"]

        except Exception as e:
            logger.error("Failed to fetch Google models", extra={"error": str(e)})
            return ["gemini-pro", "gemini-1.5-flash", "gemini-1.5-pro"]

    async def _fetch_anthropic_models(self) -> List[str]:
        """Fetch available models from Anthropic API"""
        try:
            import httpx

            api_key = settings.ANTHROPIC_API_KEY
            if not api_key:
                return [
                    "claude-3-haiku-20240307",
                    "claude-3-sonnet-20240229",
                    "claude-3-opus-20240229",
                ]

            async with httpx.AsyncClient() as client:
                await client.get(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                )

                # Anthropic doesn't have a models endpoint, so we'll infer from capabilities
                # For now, return known models
                return [
                    "claude-3-haiku-20240307",
                    "claude-3-sonnet-20240229",
                    "claude-3-opus-20240229",
                ]

        except Exception as e:
            logger.error("Failed to fetch Anthropic models", extra={"error": str(e)})
            return ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"]

    async def _fetch_huggingface_models(self) -> List[str]:
        """Fetch popular models from HuggingFace"""
        # For HuggingFace, we'll return a curated list since there's no API to list all models
        return [
            "microsoft/DialoGPT-medium",
            "google/flan-t5-base",
            "microsoft/DialoGPT-small",
            "facebook/blenderbot-400M-distill",
            "microsoft/DialoGPT-large",
        ]

    async def _fetch_local_models(self) -> List[str]:
        """Get available local models (Ollama or GGML)"""
        try:
            # Try Ollama first
            import httpx

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get("http://localhost:11434/api/tags")
                    if response.status_code == 200:
                        data = response.json()
                        models = [model.get("name", "") for model in data.get("models", [])]
                        return models if models else ["llama2", "llama3", "codellama"]
            except:
                pass

            # Fallback to common local models
            return ["llama2", "llama3", "codellama", "mistral", "vicuna"]

        except Exception as e:
            logger.error("Failed to fetch local models", extra={"error": str(e)})
            return ["llama2", "llama3", "codellama"]

    def _get_fallback_models(self, provider: str) -> List[str]:
        """Get fallback models when API calls fail"""
        fallback_maps = {
            LLMProvider.OPENAI: ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
            LLMProvider.GOOGLE: ["gemini-pro", "gemini-1.5-flash", "gemini-1.5-pro"],
            LLMProvider.ANTHROPIC: [
                "claude-3-haiku-20240307",
                "claude-3-sonnet-20240229",
                "claude-3-opus-20240229",
            ],
            LLMProvider.HUGGINGFACE: ["microsoft/DialoGPT-medium", "google/flan-t5-base"],
            LLMProvider.LOCAL: ["llama2", "llama3", "codellama"],
        }
        return fallback_maps.get(provider, [])

    def clear_cache(self, provider: str | None = None):
        """Clear cache for specific provider or all providers"""
        if provider:
            cache_key = f"models_{provider}"
            self._cache.pop(cache_key, None)
            self._cache_timestamps.pop(cache_key, None)
            logger.info(f"Cleared cache for {provider}")
        else:
            self._cache.clear()
            self._cache_timestamps.clear()
            logger.info("Cleared all model caches")

    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about current cache state"""
        return {
            "cached_providers": list(self._cache.keys()),
            "cache_timestamps": {k: v.isoformat() for k, v in self._cache_timestamps.items()},
            "cache_duration_hours": self.cache_duration.total_seconds() / 3600,
        }


# Global cache manager instance
model_cache_manager = ModelCacheManager()


class LLMFactory:
    """
    Factory class for creating LLM instances based on provider configuration.
    Supports multiple LLM providers through LangChain.
    """

    def __init__(self):
        self._llm_instances = {}
        self._supported_providers = {
            LLMProvider.OPENAI: self._create_openai_llm,
            LLMProvider.GOOGLE: self._create_google_llm,
            LLMProvider.ANTHROPIC: self._create_anthropic_llm,
            LLMProvider.HUGGINGFACE: self._create_huggingface_llm,
            LLMProvider.LOCAL: self._create_local_llm,
        }
        self._model_cache = {}  # Cache for provider models

    def get_llm(self, provider: str | None = None) -> Any:
        """
        Get or create an LLM instance for the specified provider.

        Args:
            provider: LLM provider name. If None, uses settings.LLM_PROVIDER

        Returns:
            Configured LLM instance
        """
        provider = provider or settings.LLM_PROVIDER

        if provider not in self._llm_instances:
            if provider not in self._supported_providers:
                raise ValueError(f"Unsupported LLM provider: {provider}")

            try:
                llm = self._supported_providers[provider]()
                self._llm_instances[provider] = llm
                logger.info(f"Created LLM instance for provider: {provider}")
            except Exception as e:
                logger.error(
                    f"Failed to create LLM for provider {provider}", extra={"error": str(e)}
                )
                raise

        return self._llm_instances[provider]

    def _create_openai_llm(self) -> Any:
        """Create OpenAI LLM instance using LangChain"""
        try:
            from langchain_openai import ChatOpenAI

            # Use provider-specific config or fallback to general config
            api_key = settings.OPENAI_API_KEY or settings.LLM_API_KEY
            model = settings.OPENAI_MODEL or settings.LLM_MODEL
            base_url = settings.OPENAI_BASE_URL or settings.LLM_URL

            if not api_key:
                raise ValueError("OpenAI API key not configured")

            config = {
                "model": model,
                "api_key": api_key,
                "temperature": 0.1,  # Lower temperature for structured output
                "max_tokens": 8192,  # Increased for longer video scripts
            }

            if base_url:
                config["base_url"] = base_url

            # Merge with any additional config from settings
            if settings.LLM_CONFIG:
                config.update(settings.LLM_CONFIG)

            return ChatOpenAI(**config)

        except ImportError as e:
            logger.error("langchain-openai not installed", extra={"error": str(e)})
            raise ImportError("langchain-openai is required for OpenAI provider")
        except Exception as e:
            logger.error("Failed to create OpenAI LLM", extra={"error": str(e)})
            raise

    def _create_google_llm(self) -> Any:
        """Create Google Gemini LLM instance using LangChain"""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            api_key = settings.GOOGLE_API_KEY
            model = settings.GOOGLE_MODEL

            if not api_key:
                raise ValueError("Google API key not configured")

            config = {
                "model": model,
                "api_key": api_key,
                "temperature": 0.1,
                "max_tokens": 8192,  # Increased for longer video scripts
                "convert_system_message_to_human": True,  # Required for Gemini
            }

            # Merge with any additional config from settings
            if settings.LLM_CONFIG:
                config.update(settings.LLM_CONFIG)

            return ChatGoogleGenerativeAI(**config)

        except ImportError as e:
            logger.error("langchain-google-genai not installed", extra={"error": str(e)})
            raise ImportError("langchain-google-genai is required for Google provider")
        except Exception as e:
            logger.error("Failed to create Google LLM", extra={"error": str(e)})
            raise

    def _create_anthropic_llm(self) -> Any:
        """Create Anthropic Claude LLM instance using LangChain"""
        try:
            from langchain_anthropic import ChatAnthropic

            api_key = settings.ANTHROPIC_API_KEY
            model = settings.ANTHROPIC_MODEL

            if not api_key:
                raise ValueError("Anthropic API key not configured")

            config = {
                "model": model,
                "api_key": api_key,
                "temperature": 0.1,
                "max_tokens": 8192,  # Increased for longer video scripts
            }

            # Merge with any additional config from settings
            if settings.LLM_CONFIG:
                config.update(settings.LLM_CONFIG)

            return ChatAnthropic(**config)

        except ImportError as e:
            logger.error("langchain-anthropic not installed", extra={"error": str(e)})
            raise ImportError("langchain-anthropic is required for Anthropic provider")
        except Exception as e:
            logger.error("Failed to create Anthropic LLM", extra={"error": str(e)})
            raise

    def _create_huggingface_llm(self) -> Any:
        """Create HuggingFace LLM instance using LangChain"""
        try:
            # Try to import required packages
            try:
                import torch
                from langchain_huggingface import HuggingFacePipeline
                from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
            except ImportError as e:
                logger.error(
                    "Required packages not installed for HuggingFace provider",
                    extra={"error": str(e)},
                )
                raise ImportError(
                    "Install langchain-huggingface, transformers, and torch for HuggingFace provider"
                )

            model_name = settings.HUGGINGFACE_MODEL
            api_key = settings.HUGGINGFACE_API_KEY

            # Set up authentication if provided
            if api_key:
                try:
                    from huggingface_hub import login

                    login(token=api_key)
                except ImportError:
                    logger.warning("huggingface_hub not installed, skipping authentication")

            # Determine device
            device = 0 if torch.cuda.is_available() else -1

            # Load model and tokenizer with error handling
            try:
                tokenizer = AutoTokenizer.from_pretrained(model_name)
                model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    torch_dtype=torch.float16 if device == 0 else torch.float32,
                    device_map="auto" if device == 0 else None,
                )
            except Exception as e:
                logger.error(
                    "Failed to load HuggingFace model", extra={"error": str(e), "model": model_name}
                )
                raise ValueError(f"Failed to load model {model_name}: {str(e)}")

            # Create pipeline
            hf_pipeline = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                device=device,
                max_new_tokens=8192,  # Increased for longer video scripts
                temperature=0.1,
                do_sample=False,
            )

            config = {
                "pipeline": hf_pipeline,
            }

            # Merge with any additional config from settings
            if settings.LLM_CONFIG:
                config.update(settings.LLM_CONFIG)

            return HuggingFacePipeline(**config)

        except ImportError as e:
            logger.error("HuggingFace provider dependencies not installed", extra={"error": str(e)})
            raise ImportError(
                "Install required packages: pip install langchain-huggingface transformers torch"
            )
        except Exception as e:
            logger.error("Failed to create HuggingFace LLM", extra={"error": str(e)})
            raise

    def _create_local_llm(self) -> Any:
        """Create local LLM instance using LangChain (e.g., via Ollama or local model)"""
        try:
            # Try to use Ollama if available
            try:
                # Check if Ollama is running
                import requests
                from langchain_ollama import ChatOllama

                try:
                    response = requests.get("http://localhost:11434/api/tags")
                    if response.status_code == 200:
                        config = {
                            "model": settings.LOCAL_MODEL_PATH or "llama2",
                            "temperature": 0.1,
                        }

                        if settings.LLM_CONFIG:
                            config.update(settings.LLM_CONFIG)

                        return ChatOllama(**config)
                except:
                    pass  # Ollama not available
            except ImportError:
                pass

            # Fallback to CTransformers for local GGML models
            try:
                from langchain_community.llms import CTransformers

                model_path = settings.LOCAL_MODEL_PATH
                if not model_path:
                    raise ValueError("LOCAL_MODEL_PATH must be configured for local provider")

                config = {
                    "model": model_path,
                    "model_type": settings.LOCAL_MODEL_TYPE,
                    "temperature": 0.1,
                    "max_new_tokens": 8192,  # Increased for longer video scripts
                }

                if settings.LLM_CONFIG:
                    config.update(settings.LLM_CONFIG)

                return CTransformers(**config)

            except ImportError as e:
                logger.error("No local LLM libraries available", extra={"error": str(e)})
                raise ImportError(
                    "Either langchain-ollama or langchain-community with CTransformers is required for local provider"
                )

        except Exception as e:
            logger.error("Failed to create local LLM", extra={"error": str(e)})
            raise

    def list_supported_providers(self) -> list:
        """List all supported LLM providers"""
        return list(self._supported_providers.keys())

    async def get_provider_info(self, provider: str) -> Dict[str, Any]:
        """Get information about a specific provider with cached models"""
        if provider not in self._supported_providers:
            raise ValueError(f"Unsupported provider: {provider}")

        config_example = self._get_provider_config_example(provider)

        # Get cached models or fetch fresh ones
        models = await model_cache_manager.get_models(provider)

        return {
            "provider": provider,
            "supported": True,
            "required_packages": self._get_required_packages(provider),
            "configuration": config_example,
            "supported_models": models,
        }

    def _get_required_packages(self, provider: str) -> list:
        """Get required packages for a provider"""
        package_map = {
            LLMProvider.OPENAI: ["langchain-openai"],
            LLMProvider.GOOGLE: ["langchain-google-genai"],
            LLMProvider.ANTHROPIC: ["langchain-anthropic"],
            LLMProvider.HUGGINGFACE: ["langchain-huggingface", "transformers", "torch"],
            LLMProvider.LOCAL: ["langchain-community"],  # Could also be langchain-ollama
        }
        return package_map.get(provider, [])

    def _get_provider_config_example(self, provider: str) -> Dict[str, Any]:
        """Get example configuration for a provider"""
        examples = {
            LLMProvider.OPENAI: {
                "OPENAI_API_KEY": "sk-...",
                "OPENAI_MODEL": "gpt-4",
                "supported_models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
                "LLM_CONFIG": {"temperature": 0.1, "max_tokens": 8192},
            },
            LLMProvider.GOOGLE: {
                "GOOGLE_API_KEY": "AIza...",
                "GOOGLE_MODEL": "gemini-pro",
                "supported_models": ["gemini-pro", "gemini-1.5-flash", "gemini-1.5-pro"],
            },
            LLMProvider.ANTHROPIC: {
                "ANTHROPIC_API_KEY": "sk-ant-...",
                "ANTHROPIC_MODEL": "claude-3-sonnet-20240229",
                "supported_models": [
                    "claude-3-haiku-20240307",
                    "claude-3-sonnet-20240229",
                    "claude-3-opus-20240229",
                ],
            },
            LLMProvider.HUGGINGFACE: {
                "HUGGINGFACE_MODEL": "microsoft/DialoGPT-medium",
                "HUGGINGFACE_API_KEY": "hf_...",
                "supported_models": [
                    "microsoft/DialoGPT-medium",
                    "google/flan-t5-base",
                    "microsoft/DialoGPT-small",
                ],
            },
            LLMProvider.LOCAL: {
                "LOCAL_MODEL_PATH": "/path/to/model.bin",
                "LOCAL_MODEL_TYPE": "llama",
                "supported_models": ["llama2", "llama3", "codellama"],
            },
        }
        return examples.get(provider, {})


# Global factory instance
llm_factory = LLMFactory()
