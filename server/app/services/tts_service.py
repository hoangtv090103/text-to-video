import asyncio
import logging
import os
from typing import Optional
from uuid import uuid4

import aiofiles
import httpx
from pydub import AudioSegment

from app.asset_router import exponential_backoff_retry
from app.core.config import settings
from app.core.resource_manager import resource_manager

CHATTERBOX_API_URL = settings.TTS_SERVICE_URL

logger = logging.getLogger(__name__)

ASSET_STORAGE_PATH = settings.ASSET_STORAGE_PATH

# Global HTTP client pool for better connection reuse
_tts_client_pool: httpx.AsyncClient | None = None
_pool_lock = asyncio.Lock()

async def get_tts_client() -> httpx.AsyncClient:
    """
    Get or create a shared HTTP client for TTS requests with optimized connection pooling.
    
    Uses a global client pool with proper connection management for better performance
    while handling the slow TTS server appropriately.
    """
    global _tts_client_pool
    
    async with _pool_lock:
        if _tts_client_pool is None or _tts_client_pool.is_closed:
            timeout_config = httpx.Timeout(
                connect=30.0,  # 30s to establish connection
                read=1200.0,   # 20 minutes to read response (increased for stability)
                write=60.0,    # 1 minute to write request
                pool=30.0      # 30s for pool operations
            )
            limits = httpx.Limits(
                max_keepalive_connections=2,  # Allow some keepalive for efficiency
                max_connections=3,           # Limit total connections
                keepalive_expiry=60.0        # Short keepalive to avoid stale connections
            )
            _tts_client_pool = httpx.AsyncClient(
                timeout=timeout_config,
                limits=limits,
                http2=False  # Disable HTTP/2 to avoid protocol issues
            )
            logger.info("Created new TTS client pool")
    
    return _tts_client_pool


async def close_tts_client():
    """Close the global TTS client pool"""
    global _tts_client_pool
    
    async with _pool_lock:
        if _tts_client_pool and not _tts_client_pool.is_closed:
            await _tts_client_pool.aclose()
            _tts_client_pool = None
            logger.info("Closed TTS client pool")


async def check_tts_service_health() -> bool:
    """Quick health check for TTS service before making requests."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{CHATTERBOX_API_URL.replace('/v1/audio/speech', '/v1/health')}")
            return response.status_code == 200
    except Exception as e:
        logger.warning(f"TTS health check failed: {e}")
        return False


@exponential_backoff_retry(max_retries=3, base_delay=10.0)
async def generate_audio(scene: dict) -> dict:
    """
    Asynchronous TTS service that generates audio from scene narration text.

    Args:
        scene: Scene dictionary containing narration_text and other metadata

    Returns:
        Dictionary with audio path, duration, and status

    Raises:
        Exception: On request failures or service errors
    """
    seg_id = scene.get("id", "")
    job_id = scene.get("job_id", "unknown")
    text_input = scene.get("narration_text", "")

    if not text_input:
        logger.warning("No narration text provided for scene")
        return {
            "status": "success_no_text",
            "message": "No narration text provided",
            "path": None,
            "duration": 0,
        }
    
    # Health check before processing
    logger.info(f"Checking TTS service health before processing scene {seg_id}")
    tts_healthy = await check_tts_service_health()
    if not tts_healthy:
        logger.error(f"TTS service unhealthy before processing scene {seg_id}, will retry")
        # Wait a bit for service to recover
        await asyncio.sleep(5)
        raise Exception("TTS service is not healthy")

    # Check cache first for TTS audio
    from app.utils.cache import get_from_cache, set_cache
    cached_result = await get_from_cache("tts", text_input)

    # Ensure asset storage directory exists
    os.makedirs(ASSET_STORAGE_PATH, exist_ok=True)

    # Generate unique file path for this segment with job_id
    file_path = os.path.join(ASSET_STORAGE_PATH, f"job_{job_id}_segment_{seg_id}.wav")

    if cached_result and cached_result.get("path"):
        # Cache hit - copy the cached audio file to new path for this segment
        import shutil
        cached_path = cached_result.get("path")
        if os.path.exists(cached_path):
            try:
                await asyncio.to_thread(shutil.copy2, cached_path, file_path)
                logger.info(
                    f"Using cached TTS audio (copied to new file for segment {seg_id})",
                    extra={
                        "segment_id": seg_id,
                        "cached_path": cached_path,
                        "new_path": file_path,
                        "duration": cached_result.get("duration")
                    }
                )
                return {
                    "path": file_path,
                    "duration": cached_result.get("duration", 0),
                    "status": "success",
                    "cached": True
                }
            except Exception as copy_error:
                logger.warning(
                    "Failed to copy cached audio file, will regenerate",
                    extra={"segment_id": seg_id, "error": str(copy_error)}
                )
        else:
            logger.warning(
                "Cached audio file not found, will regenerate",
                extra={"segment_id": seg_id, "cached_path": cached_path}
            )

    payload = {
        "input": text_input,
        "voice": "alloy",
        "response_format": "wav",
        "speed": 1,
        "exaggeration": 0.2,  # Lower values = faster generation, more stable
        "cfg_weight": 0.4,  # Lower values = faster generation, more stable
        "temperature": 0.2,  # Lower values = more stable generation
        "max_chunk_length": 200,  # Smaller chunks for stability
        "max_total_length": 2000,  # Limit total length
    }

    # Use resource manager to acquire TTS slot
    async with resource_manager.acquire_tts_slot(str(seg_id)):
        logger.info(
            f"Acquired TTS slot for scene {seg_id}",
            extra={
                "segment_id": seg_id,
                "text_length": len(text_input),
                "tts_url": CHATTERBOX_API_URL
            }
        )
        
        # Get shared client from pool
        client = await get_tts_client()
        
        try:
            # Stream download and save asynchronously for better memory usage
            async with client.stream("POST", f"{CHATTERBOX_API_URL}", json=payload) as response:
                response.raise_for_status()
                logger.info(
                    f"TTS response received for scene {seg_id}",
                    extra={
                        "segment_id": seg_id,
                        "status_code": response.status_code,
                        "content_type": response.headers.get("content-type")
                    }
                )
                async with aiofiles.open(file_path, "wb") as f:
                    bytes_written = 0
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        await f.write(chunk)
                        bytes_written += len(chunk)
                logger.info(
                    f"TTS audio stream completed for scene {seg_id}",
                    extra={"segment_id": seg_id, "bytes_written": bytes_written}
                )
        except httpx.RemoteProtocolError as e:
            logger.error(
                f"TTS server disconnected unexpectedly for scene {seg_id}",
                extra={
                    "segment_id": seg_id,
                    "error": str(e),
                    "error_type": "RemoteProtocolError",
                    "tts_url": CHATTERBOX_API_URL,
                    "suggestion": "TTS service may be overloaded or crashed"
                },
                exc_info=True
            )
            # Wait before retry to give service time to recover
            await asyncio.sleep(15)
            raise Exception(f"TTS server disconnected: {str(e)}") from e
        except httpx.HTTPStatusError as e:
            logger.error(
                f"TTS returned error status for scene {seg_id}",
                extra={
                    "segment_id": seg_id,
                    "status_code": e.response.status_code,
                    "error": str(e),
                    "error_type": "HTTPStatusError",
                    "tts_url": CHATTERBOX_API_URL,
                    "response_text": e.response.text[:500] if hasattr(e.response, 'text') else None
                },
                exc_info=True
            )
            raise Exception(f"TTS HTTP error: {str(e)}") from e
        except Exception as e:
            logger.error(
                f"TTS request failed for scene {seg_id}",
                extra={
                    "segment_id": seg_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "tts_url": CHATTERBOX_API_URL
                },
                exc_info=True
            )
            raise Exception(f"TTS request failed: {str(e)}") from e

    logger.info(f"Successfully saved TTS audio to {file_path}", extra={"segment_id": seg_id})

    # Get the duration of the audio file
    duration = await get_audio_duration(file_path)
    logger.info(
        "Successfully retrieved duration of TTS audio",
        extra={"segment_id": seg_id, "duration": duration},
    )

    result = {"path": file_path, "duration": duration, "status": "success"}
    # Cache the result
    await set_cache("tts", text_input, result)
    return result

async def get_audio_duration(file_path):
    try:
        audio = AudioSegment.from_file(file_path)
        return audio.duration_seconds
    except Exception as e:
        logger.error("Failed to get audio duration", extra={
            "error_type": type(e).__name__,
            "error": str(e),
            "file_path": file_path
        })
        return None
