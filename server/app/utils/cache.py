"""
Simple cache utility for LLM results, TTS audio, and visual assets.
Uses Redis for storage with configurable TTL.
"""
import hashlib
import json
import logging
from typing import Optional, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

# Cache TTL settings (in seconds)
CACHE_TTL = {
    "llm": 3600,      # 1 hour for LLM results
    "tts": 1800,      # 30 minutes for TTS audio
    "visual": 1800,   # 30 minutes for visual assets
}

def generate_cache_key(prefix: str, content: str) -> str:
    """Generate a consistent cache key from content."""
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    return f"cache:{prefix}:{content_hash}"

async def get_from_cache(prefix: str, content: str) -> Optional[Any]:
    """Get cached result if available."""
    try:
        from app.services.redis_service import redis_service, REDIS_AVAILABLE
        
        if not REDIS_AVAILABLE or not redis_service:
            return None
            
        cache_key = generate_cache_key(prefix, content)
        client = await redis_service.get_client()
        cached_data = await client.get(cache_key)
        
        if cached_data:
            logger.info(f"Cache hit for {prefix}", extra={"cache_key": cache_key})
            return json.loads(cached_data)
            
    except Exception as e:
        logger.warning(f"Cache get failed for {prefix}", extra={"error": str(e)})
    
    return None

async def set_cache(prefix: str, content: str, result: Any) -> None:
    """Cache the result with appropriate TTL."""
    try:
        from app.services.redis_service import redis_service, REDIS_AVAILABLE
        
        if not REDIS_AVAILABLE or not redis_service:
            return
            
        cache_key = generate_cache_key(prefix, content)
        client = await redis_service.get_client()
        
        # Store with TTL
        ttl = CACHE_TTL.get(prefix, 1800)  # Default 30 minutes
        await client.setex(cache_key, ttl, json.dumps(result))
        
        logger.info(f"Cached {prefix} result", extra={
            "cache_key": cache_key, 
            "ttl": ttl
        })
        
    except Exception as e:
        logger.warning(f"Cache set failed for {prefix}", extra={"error": str(e)})
