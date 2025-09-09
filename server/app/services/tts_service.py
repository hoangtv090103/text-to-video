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

ASSET_STORAGE_PATH = "/tmp/assets"

@exponential_backoff_retry(max_retries=3, base_delay=1.0)
async def generate_audio(scene: Dict) -> Dict:
    """
    Mock TTS service that generates audio from scene narration text.

    Args:
        scene: Scene dictionary containing narration_text and other metadata

    Returns:
        Dictionary with audio path, duration, and status

    Raises:
        Exception: Randomly fails ~15% of the time to simulate service failures
    """
    seg_id = scene.get("id", "")
    text_input = scene.get("narration_text", "")
    if not text_input:
        logging.warning("No narration text provided for scene")
        return {"status": "success_no_text", "message": "No narration text provided", "path": None, "duration": 0}

    payload = {
        "input": text_input,
        "voice": "alloy",
        "response_format": "wav",
        "speed": 1,
        "stream_format": "audio",
        "exaggeration": 0.25,
        "cfg_weight": 1,
        "temperature": 0.05,
        "streaming_chunk_size": 50,
        # "streaming_strategy": "string",
        "streaming_buffer_size": 1,
        # "streaming_quality": "string"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{CHATTERBOX_API_URL}", json=payload)
        response.raise_for_status()

        os.makedirs(ASSET_STORAGE_PATH, exist_ok=True)

        file_path = os.path.join(ASSET_STORAGE_PATH, f"segment_{seg_id}_{uuid4()}.wav")

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
        logger.error(f"Failed to get duration of audio file {file_path}", extra={"error": str(e)})
        return None
