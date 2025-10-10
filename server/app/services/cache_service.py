"""
Cache service with TTL-based expiration.

Provides in-memory caching for LLM responses, TTS audio, and visual assets
to reduce external API calls and improve performance.
"""

import asyncio
import contextlib
import hashlib
import time
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class CacheEntry:
    """Single cache entry with value and expiration time."""

    def __init__(self, value: Any, ttl_seconds: int):
        """
        Initialize cache entry.

        Args:
            value: The cached value
            ttl_seconds: Time-to-live in seconds
        """
        self.value = value
        self.expires_at = time.time() + ttl_seconds
        self.created_at = datetime.utcnow()

    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        return time.time() > self.expires_at


class CacheService:
    """
    In-memory cache with TTL-based expiration.

    Features:
    - TTL-based expiration per entry
    - Automatic cleanup of expired entries
    - Hash-based key generation for complex objects
    - Thread-safe operations
    """

    def __init__(self, cleanup_interval: int = 300):
        """
        Initialize cache service.

        Args:
            cleanup_interval: Seconds between cleanup runs (default: 5 minutes)
        """
        self._cache: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
        self._cleanup_interval = cleanup_interval
        self._cleanup_task: asyncio.Task | None = None
        logger.info("Cache service initialized", cleanup_interval=cleanup_interval)

    async def start_cleanup_task(self):
        """Start the background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Cache cleanup task started")

    async def stop_cleanup_task(self):
        """Stop the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            logger.info("Cache cleanup task stopped")

    async def _cleanup_loop(self):
        """Background task to periodically clean expired entries."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Cache cleanup error", error=str(exc))

    async def _cleanup_expired(self):
        """Remove all expired entries from cache."""
        async with self._lock:
            expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]
            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.info("Cleaned expired cache entries", count=len(expired_keys))

    @staticmethod
    def generate_key(*args, **kwargs) -> str:
        """
        Generate a cache key from arguments.

        Args:
            *args: Positional arguments to hash
            **kwargs: Keyword arguments to hash

        Returns:
            MD5 hash of the arguments as hex string
        """
        # Combine args and kwargs into a single string
        key_parts = [str(arg) for arg in args]
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key_string = ":".join(key_parts)

        # Generate MD5 hash
        return hashlib.md5(key_string.encode()).hexdigest()

    async def get(self, key: str) -> Any | None:
        """
        Retrieve value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                logger.debug("Cache miss", key=key)
                return None

            if entry.is_expired():
                del self._cache[key]
                logger.debug("Cache expired", key=key)
                return None

            logger.debug(
                "Cache hit",
                key=key,
                age_seconds=int(time.time() - entry.expires_at + entry.expires_at - time.time()),
            )
            return entry.value

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """
        Store value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (default: 1 hour)
        """
        async with self._lock:
            self._cache[key] = CacheEntry(value, ttl)
            logger.debug("Cache set", key=key, ttl=ttl, cache_size=len(self._cache))

    async def delete(self, key: str) -> bool:
        """
        Delete a cache entry.

        Args:
            key: Cache key

        Returns:
            True if entry existed and was deleted, False otherwise
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug("Cache entry deleted", key=key)
                return True
            return False

    async def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info("Cache cleared", entries_removed=count)
            return count

    async def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats (size, oldest entry, etc.)
        """
        async with self._lock:
            total_entries = len(self._cache)
            expired_count = sum(1 for entry in self._cache.values() if entry.is_expired())
            active_count = total_entries - expired_count

            oldest_entry = None
            if self._cache:
                oldest_entry = min(
                    (entry.created_at for entry in self._cache.values()), default=None
                )

            return {
                "total_entries": total_entries,
                "active_entries": active_count,
                "expired_entries": expired_count,
                "oldest_entry": oldest_entry.isoformat() if oldest_entry else None,
            }


# Global cache instance
cache_service = CacheService(cleanup_interval=300)  # 5 minutes


# Convenience functions with preset TTLs
async def cache_llm_response(prompt: str, provider: str, model: str, response: Any) -> None:
    """
    Cache LLM response with 1 hour TTL.

    Args:
        prompt: The prompt text
        provider: LLM provider name
        model: Model name
        response: The LLM response to cache
    """
    key = CacheService.generate_key("llm", prompt, provider, model)
    await cache_service.set(key, response, ttl=3600)  # 1 hour


async def get_cached_llm_response(prompt: str, provider: str, model: str) -> Any | None:
    """
    Retrieve cached LLM response.

    Args:
        prompt: The prompt text
        provider: LLM provider name
        model: Model name

    Returns:
        Cached response if available, None otherwise
    """
    key = CacheService.generate_key("llm", prompt, provider, model)
    return await cache_service.get(key)


async def cache_tts_audio(narration_text: str, voice_id: str, audio_data: Any) -> None:
    """
    Cache TTS audio with 24 hour TTL.

    Args:
        narration_text: The text that was narrated
        voice_id: Voice ID used
        audio_data: The audio data to cache
    """
    key = CacheService.generate_key("tts", narration_text, voice_id)
    await cache_service.set(key, audio_data, ttl=86400)  # 24 hours


async def get_cached_tts_audio(narration_text: str, voice_id: str) -> Any | None:
    """
    Retrieve cached TTS audio.

    Args:
        narration_text: The text that was narrated
        voice_id: Voice ID used

    Returns:
        Cached audio data if available, None otherwise
    """
    key = CacheService.generate_key("tts", narration_text, voice_id)
    return await cache_service.get(key)


async def cache_visual_asset(visual_type: str, prompt: str, asset_path: str) -> None:
    """
    Cache visual asset path with 24 hour TTL.

    Args:
        visual_type: Type of visual (slide, diagram, graph, etc.)
        prompt: The visual prompt
        asset_path: Path to the generated asset
    """
    key = CacheService.generate_key("visual", visual_type, prompt)
    await cache_service.set(key, asset_path, ttl=86400)  # 24 hours


async def get_cached_visual_asset(visual_type: str, prompt: str) -> str | None:
    """
    Retrieve cached visual asset path.

    Args:
        visual_type: Type of visual (slide, diagram, graph, etc.)
        prompt: The visual prompt

    Returns:
        Cached asset path if available, None otherwise
    """
    key = CacheService.generate_key("visual", visual_type, prompt)
    return await cache_service.get(key)
