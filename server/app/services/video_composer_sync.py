"""
Synchronous video composition service using MoviePy.
Applies Ken Burns effect, syncs audio with visuals, and generates final MP4.
"""
from __future__ import annotations

import contextlib
import logging
import os

from app.core.config import settings

logger = logging.getLogger(__name__)

# Video output configuration (persistent)
OUTPUT_DIR = settings.VIDEO_OUTPUT_PATH
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _ken_burns(clip, zoom: float = 0.05):
    """
    Apply a slow zoom-in effect (Ken Burns) over the clip duration.

    Args:
        clip: ImageClip to apply effect to
        zoom: Maximum zoom factor (default 0.05 = 5% zoom)

    Returns:
        Modified clip with Ken Burns effect
    """
    from moviepy import vfx

    # Slow zoom-in over the clip duration (MoviePy 2.x API)
    return clip.with_effects([vfx.Resize(lambda t: 1 + zoom * (t / max(clip.duration, 0.001)))])


def compose_video_sync(scenes: list[dict], job_id: str) -> dict:
    """
    Compose final video from scene assets synchronously.

    Args:
        scenes: List of scene dicts with audio and visual paths
        job_id: Job identifier for output naming

    Returns:
        Dict with status, video_path, duration, and fps
    """
    try:
        from moviepy import AudioFileClip, ImageClip, concatenate_videoclips

        clips = []

        for scene in scenes:
            img_path = scene.get("visual", {}).get("path")
            aud_path = scene.get("audio", {}).get("path")
            dur = float(scene.get("audio", {}).get("duration") or 0.0)

            if not (img_path and aud_path and dur > 0):
                logger.warning(
                    "Skipping invalid scene",
                    extra={
                        "job_id": job_id,
                        "scene_id": scene.get("scene_id"),
                        "has_image": bool(img_path),
                        "has_audio": bool(aud_path),
                        "duration": dur,
                    },
                )
                continue

            # Verify files exist
            if not os.path.exists(img_path):
                logger.warning(
                    "Image file not found, skipping scene",
                    extra={"job_id": job_id, "scene_id": scene.get("scene_id"), "path": img_path},
                )
                continue

            if not os.path.exists(aud_path):
                logger.warning(
                    "Audio file not found, skipping scene",
                    extra={"job_id": job_id, "scene_id": scene.get("scene_id"), "path": aud_path},
                )
                continue

            try:
                # Create image clip with duration matching audio (MoviePy 2.x API)
                img = ImageClip(img_path, duration=dur)

                # Apply Ken Burns zoom effect
                img = _ken_burns(img, zoom=0.06)

                # Load audio and attach to clip
                audio = AudioFileClip(aud_path)
                clip = img.with_audio(audio)
                clips.append(clip)

                logger.info(
                    "Scene clip created",
                    extra={
                        "job_id": job_id,
                        "scene_id": scene.get("scene_id"),
                        "duration": dur,
                    },
                )
            except Exception as scene_error:
                logger.error(
                    "Failed to create scene clip",
                    extra={
                        "job_id": job_id,
                        "scene_id": scene.get("scene_id"),
                        "error": str(scene_error),
                    },
                )
                continue

        if not clips:
            return {"status": "error", "error": "No valid scene clips to compose"}

        # Concatenate all clips
        logger.info(
            "Concatenating video clips", extra={"job_id": job_id, "clip_count": len(clips)}
        )
        video = concatenate_videoclips(clips, method="compose")

        # Write final video with H.264 + AAC
        out_path = os.path.join(OUTPUT_DIR, f"video_{job_id}.mp4")
        logger.info("Writing final video", extra={"job_id": job_id, "output_path": out_path})

        video.write_videofile(
            out_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            logger=None,  # Suppress MoviePy's logger output
        )

        duration = video.duration

        # Clean up clips
        for clip in clips:
            with contextlib.suppress(Exception):
                clip.close()

        with contextlib.suppress(Exception):
            video.close()

        logger.info(
            "Video composition completed",
            extra={"job_id": job_id, "duration": duration, "output_path": out_path},
        )

        return {
            "status": "success",
            "video_path": out_path,
            "duration": duration,
            "fps": 24,
        }

    except Exception as e:
        logger.error(
            "Video composition failed", extra={"job_id": job_id, "error": str(e)}, exc_info=True
        )
        return {"status": "error", "error": str(e)}
