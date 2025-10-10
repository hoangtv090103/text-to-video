import logging
import os
import time
from typing import Dict
from uuid import uuid4

import requests
from pydub import AudioSegment

from app.core.config import settings

CHATTERBOX_API_URL = settings.TTS_SERVICE_URL

logger = logging.getLogger(__name__)

ASSET_STORAGE_PATH = settings.ASSET_STORAGE_PATH


def exponential_backoff_retry_sync(max_retries=3, base_delay=1.0):
    """
    Synchronous decorator for exponential backoff retry logic.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = Exception("Unknown error")

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} retries",
                            extra={"error": str(e), "attempt": attempt + 1},
                        )
                        raise e

                    delay = base_delay * (2**attempt)
                    logger.warning(
                        f"Function {func.__name__} failed, retrying in {delay}s",
                        extra={"error": str(e), "attempt": attempt + 1, "delay": delay},
                    )
                    time.sleep(delay)

            raise last_exception

        return wrapper

    return decorator


@exponential_backoff_retry_sync(max_retries=3, base_delay=1.0)
def generate_audio_sync(scene: Dict) -> Dict:
    """
    Synchronous TTS service that generates audio from scene narration text.

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

    payload = {
        "input": text_input,
        "voice": "alloy",
        "response_format": "wav",
        "speed": 1,
        "exaggeration": 0.25,  # Lower values = faster generation
        "cfg_weight": 0.5,  # Lower values = faster generation
        "temperature": 0.3,  # Higher values = faster generation
    }

    # Use requests instead of httpx for synchronous calls
    response = requests.post(CHATTERBOX_API_URL, json=payload)
    response.raise_for_status()

    # Ensure asset storage directory exists
    os.makedirs(ASSET_STORAGE_PATH, exist_ok=True)

    # Generate unique file path
    file_path = os.path.join(ASSET_STORAGE_PATH, f"segment_{seg_id}_{uuid4()}.wav")

    # Save audio file
    with open(file_path, "wb") as f:
        f.write(response.content)

    logger.info(
        "Successfully saved TTS audio",
        extra={"segment_id": seg_id, "file_path": file_path, "file_size": len(response.content)},
    )

    # Get the duration of the audio file
    duration = get_audio_duration_sync(file_path)
    logger.info(
        "Successfully retrieved duration of TTS audio",
        extra={"segment_id": seg_id, "duration": duration},
    )

    return {"path": file_path, "duration": duration, "status": "success"}


def get_audio_duration_sync(file_path: str) -> float:
    """
    Get the duration of an audio file synchronously.

    Args:
        file_path: Path to the audio file

    Returns:
        Duration in seconds, or 0 if failed
    """
    try:
        audio = AudioSegment.from_file(file_path)
        return audio.duration_seconds
    except Exception as e:
        logger.error(
            "Failed to get duration of audio file", extra={"file_path": file_path, "error": str(e)}
        )
        return 0.0
