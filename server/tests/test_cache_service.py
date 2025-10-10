"""
Unit tests for cache service.
"""

import asyncio

import pytest

from app.services.cache_service import (
    CacheEntry,
    CacheService,
    cache_llm_response,
    cache_service,
    cache_tts_audio,
    cache_visual_asset,
    get_cached_llm_response,
    get_cached_tts_audio,
    get_cached_visual_asset,
)


class TestCacheEntry:
    """Tests for CacheEntry class."""

    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        entry = CacheEntry("test_value", ttl_seconds=60)
        assert entry.value == "test_value"
        assert not entry.is_expired()

    def test_cache_entry_expiration(self):
        """Test cache entry expires after TTL."""
        entry = CacheEntry("test_value", ttl_seconds=0)
        # Sleep briefly to ensure expiration
        import time

        time.sleep(0.1)
        assert entry.is_expired()


class TestCacheService:
    """Tests for CacheService class."""

    @pytest.fixture
    async def cache(self):
        """Create a fresh cache instance for each test."""
        cache = CacheService(cleanup_interval=1)
        yield cache
        await cache.clear()
        await cache.stop_cleanup_task()

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache):
        """Test basic set and get operations."""
        await cache.set("test_key", "test_value", ttl=60)
        value = await cache.get("test_key")
        assert value == "test_value"

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, cache):
        """Test getting a key that doesn't exist."""
        value = await cache.get("nonexistent")
        assert value is None

    @pytest.mark.asyncio
    async def test_expiration(self, cache):
        """Test that entries expire after TTL."""
        await cache.set("expire_key", "expire_value", ttl=1)

        # Value should exist initially
        value = await cache.get("expire_key")
        assert value == "expire_value"

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Value should be expired
        value = await cache.get("expire_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_delete(self, cache):
        """Test deleting a cache entry."""
        await cache.set("delete_key", "delete_value", ttl=60)

        # Verify it exists
        value = await cache.get("delete_key")
        assert value == "delete_value"

        # Delete it
        deleted = await cache.delete("delete_key")
        assert deleted is True

        # Verify it's gone
        value = await cache.get("delete_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, cache):
        """Test deleting a key that doesn't exist."""
        deleted = await cache.delete("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_clear(self, cache):
        """Test clearing all cache entries."""
        await cache.set("key1", "value1", ttl=60)
        await cache.set("key2", "value2", ttl=60)
        await cache.set("key3", "value3", ttl=60)

        # Clear cache
        count = await cache.clear()
        assert count == 3

        # Verify all gone
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert await cache.get("key3") is None

    @pytest.mark.asyncio
    async def test_generate_key(self):
        """Test key generation from arguments."""
        key1 = CacheService.generate_key("arg1", "arg2", param1="value1")
        key2 = CacheService.generate_key("arg1", "arg2", param1="value1")
        key3 = CacheService.generate_key("arg1", "arg2", param1="value2")

        # Same arguments should produce same key
        assert key1 == key2

        # Different arguments should produce different key
        assert key1 != key3

    @pytest.mark.asyncio
    async def test_cleanup_task(self, cache):
        """Test background cleanup task."""
        # Start cleanup task
        await cache.start_cleanup_task()

        # Add some entries with short TTL
        await cache.set("temp1", "value1", ttl=1)
        await cache.set("temp2", "value2", ttl=1)

        # Wait for expiration and cleanup
        await asyncio.sleep(2)

        # Entries should be cleaned up
        stats = await cache.get_stats()
        assert stats["expired_entries"] == 0

        # Stop cleanup task
        await cache.stop_cleanup_task()

    @pytest.mark.asyncio
    async def test_get_stats(self, cache):
        """Test getting cache statistics."""
        await cache.set("key1", "value1", ttl=60)
        await cache.set("key2", "value2", ttl=1)

        # Get stats before expiration
        stats = await cache.get_stats()
        assert stats["total_entries"] == 2
        assert stats["active_entries"] >= 1

        # Wait for one to expire
        await asyncio.sleep(1.5)

        # Get stats after expiration
        stats = await cache.get_stats()
        assert stats["expired_entries"] >= 1


class TestLLMCaching:
    """Tests for LLM caching convenience functions."""

    @pytest.mark.asyncio
    async def test_cache_and_get_llm_response(self):
        """Test caching and retrieving LLM responses."""
        prompt = "What is the meaning of life?"
        provider = "openai"
        model = "gpt-4"
        response = {"text": "42", "tokens": 100}

        # Cache the response
        await cache_llm_response(prompt, provider, model, response)

        # Retrieve it
        cached = await get_cached_llm_response(prompt, provider, model)
        assert cached == response

    @pytest.mark.asyncio
    async def test_different_prompts_different_cache(self):
        """Test that different prompts don't collide."""
        response1 = {"text": "Answer 1"}
        response2 = {"text": "Answer 2"}

        await cache_llm_response("prompt1", "openai", "gpt-4", response1)
        await cache_llm_response("prompt2", "openai", "gpt-4", response2)

        cached1 = await get_cached_llm_response("prompt1", "openai", "gpt-4")
        cached2 = await get_cached_llm_response("prompt2", "openai", "gpt-4")

        assert cached1 == response1
        assert cached2 == response2


class TestTTSCaching:
    """Tests for TTS caching convenience functions."""

    @pytest.mark.asyncio
    async def test_cache_and_get_tts_audio(self):
        """Test caching and retrieving TTS audio."""
        narration = "Hello world"
        voice_id = "en-US-female"
        audio_data = b"fake_audio_bytes"

        # Cache the audio
        await cache_tts_audio(narration, voice_id, audio_data)

        # Retrieve it
        cached = await get_cached_tts_audio(narration, voice_id)
        assert cached == audio_data

    @pytest.mark.asyncio
    async def test_different_voices_different_cache(self):
        """Test that different voices don't collide."""
        audio1 = b"audio1"
        audio2 = b"audio2"

        await cache_tts_audio("hello", "voice1", audio1)
        await cache_tts_audio("hello", "voice2", audio2)

        cached1 = await get_cached_tts_audio("hello", "voice1")
        cached2 = await get_cached_tts_audio("hello", "voice2")

        assert cached1 == audio1
        assert cached2 == audio2


class TestVisualCaching:
    """Tests for visual asset caching convenience functions."""

    @pytest.mark.asyncio
    async def test_cache_and_get_visual_asset(self):
        """Test caching and retrieving visual assets."""
        visual_type = "slide"
        prompt = "A beautiful sunset"
        asset_path = "/tmp/visuals/sunset.png"

        # Cache the asset
        await cache_visual_asset(visual_type, prompt, asset_path)

        # Retrieve it
        cached = await get_cached_visual_asset(visual_type, prompt)
        assert cached == asset_path

    @pytest.mark.asyncio
    async def test_different_types_different_cache(self):
        """Test that different visual types don't collide."""
        path1 = "/tmp/slide.png"
        path2 = "/tmp/diagram.png"

        await cache_visual_asset("slide", "test", path1)
        await cache_visual_asset("diagram", "test", path2)

        cached1 = await get_cached_visual_asset("slide", "test")
        cached2 = await get_cached_visual_asset("diagram", "test")

        assert cached1 == path1
        assert cached2 == path2


class TestGlobalCacheInstance:
    """Tests for the global cache_service instance."""

    @pytest.mark.asyncio
    async def test_global_instance(self):
        """Test that global cache instance works."""
        await cache_service.set("global_key", "global_value", ttl=60)
        value = await cache_service.get("global_key")
        assert value == "global_value"

        # Clean up
        await cache_service.delete("global_key")
