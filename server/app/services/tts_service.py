import httpx
import os
import logging
from typing import Dict
from uuid import uuid4
from pydub import AudioSegment

from app.core.config import settings
from app.asset_router import exponential_backoff_retry
CHATTERBOX_API_URL = settings.TTS_SERVICE_URL

logger = logging.getLogger(__name__)

ASSET_STORAGE_PATH = settings.ASSET_STORAGE_PATH

# Shared HTTP client with connection pooling
_tts_client = None

def get_tts_client():
    """Get or create shared HTTP client with connection pooling."""
    global _tts_client
    if _tts_client is None or _tts_client.is_closed:
        timeout_config = httpx.Timeout(
            connect=10.0, read=60.0, write=10.0, pool=5.0
        )
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        _tts_client = httpx.AsyncClient(timeout=timeout_config, limits=limits)
    return _tts_client

@exponential_backoff_retry(max_retries=3, base_delay=1.0)
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
            "duration": 0
        }

    payload = {
        "input": text_input,
        "voice": "alloy",
        "response_format": "wav",
        "speed": 1,
        "exaggeration": 0.25,  # Lower values = faster generation
        "cfg_weight": 0.5,     # Lower values = faster generation
        "temperature": 0.3,    # Higher values = faster generation
    }

    # Use shared HTTP client with connection pooling
    client = get_tts_client()
    response = await client.post(f"{CHATTERBOX_API_URL}", json=payload)
    response.raise_for_status()

    # Ensure asset storage directory exists
    os.makedirs(ASSET_STORAGE_PATH, exist_ok=True)

    # Generate unique file path
    file_path = os.path.join(ASSET_STORAGE_PATH, f"segment_{seg_id}_{uuid4()}.wav")

    # Save audio file
    with open(file_path, "wb") as f:
        f.write(response.content)

    logger.info(f"Successfully saved TTS audio to {file_path}", extra={"segment_id": seg_id})

    # Get the duration of the audio file
    duration = await get_audio_duration(file_path)
    logger.info("Successfully retrieved duration of TTS audio", extra={"segment_id": seg_id, "duration": duration})

    return {
        "path": file_path,
        "duration": duration,
        "status": "success"
    }

async def get_audio_duration(file_path):
    try:
        audio = AudioSegment.from_file(file_path)
        duration = audio.duration_seconds
        return duration
    except Exception as e:
        logger.error("Failed to get audio duration", extra={
            "error_type": type(e).__name__,
            "error": str(e),
            "file_path": file_path
        })
        return None
