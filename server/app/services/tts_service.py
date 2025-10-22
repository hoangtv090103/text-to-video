import asyncio
import logging
import os
import aiofiles
from typing import Dict
from uuid import uuid4

import httpx
from pydub import AudioSegment

from app.asset_router import exponential_backoff_retry
from app.core.config import settings

CHATTERBOX_API_URL = settings.TTS_SERVICE_URL

logger = logging.getLogger(__name__)

ASSET_STORAGE_PATH = settings.ASSET_STORAGE_PATH

# Semaphore to limit concurrent TTS requests (CPU TTS can't handle many parallel requests)
# CRITICAL: Set to 1 for CPU-based TTS to prevent server overload and connection errors
_tts_semaphore = asyncio.Semaphore(1)  # Only 1 concurrent TTS request to prevent overload

def create_tts_client():
    """
    Create a fresh HTTP client for TTS requests.

    **CRITICAL**: We create a new client per request instead of reusing a global one
    because the CPU-based TTS server is very slow (60-120s per request) and connection
    pooling with keepalive causes "Server disconnected without sending a response" errors
    when connections become stale between long requests.

    By disabling keepalive (max_keepalive_connections=0), each request gets a fresh
    connection, preventing the stale connection issue entirely.
    """
    timeout_config = httpx.Timeout(
        connect=30.0,  # 30s to establish connection
        read=600.0,    # 10 minutes to read response (TTS can be slow)
        write=60.0,    # 1 minute to write request
        pool=15.0      # 15s for pool operations
    )
    limits = httpx.Limits(max_keepalive_connections=0, max_connections=5)
    return httpx.AsyncClient(
        timeout=timeout_config,
        limits=limits,
        http2=False  # Disable HTTP/2 to avoid protocol issues
    )


@exponential_backoff_retry(max_retries=2, base_delay=5.0)
async def generate_audio(scene: Dict) -> Dict:
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
    text_input = scene.get("narration_text", "")

    if not text_input:
        logger.warning("No narration text provided for scene")
        return {
            "status": "success_no_text",
            "message": "No narration text provided",
            "path": None,
            "duration": 0,
        }

    # Check cache first for TTS audio
    from app.utils.cache import get_from_cache, set_cache
    cached_result = await get_from_cache("tts", text_input)
    if cached_result:
        return cached_result

    payload = {
        "input": text_input,
        "voice": "alloy",
        "response_format": "wav",
        "speed": 1,
        "exaggeration": 0.25,  # Lower values = faster generation
        "cfg_weight": 0.5,  # Lower values = faster generation
        "temperature": 0.3,  # Higher values = faster generation
    }

    # Create a fresh client per request to avoid stale connection pooling issues
    # (CPU TTS is very slow, connections can become stale between requests)
    client = create_tts_client()

    # Ensure asset storage directory exists
    os.makedirs(ASSET_STORAGE_PATH, exist_ok=True)

    # Generate unique file path
    file_path = os.path.join(ASSET_STORAGE_PATH, f"segment_{seg_id}_{uuid4()}.wav")

    # Limit concurrent TTS requests to avoid overwhelming CPU-based TTS server
    async with _tts_semaphore:
        logger.info(
            f"Acquired TTS slot for scene {seg_id}",
            extra={
                "segment_id": seg_id,
                "text_length": len(text_input),
                "tts_url": CHATTERBOX_API_URL
            }
        )
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
            raise
        finally:
            # Always close the client to free resources
            await client.aclose()
            logger.debug(f"TTS client closed for scene {seg_id}", extra={"segment_id": seg_id})

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
