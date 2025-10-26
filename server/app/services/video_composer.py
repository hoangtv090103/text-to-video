"""
Improved synchronous video composition service using MoviePy.
Properly handles audio-visual synchronization and concatenation.
"""
from __future__ import annotations

import contextlib
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

# Video output configuration (persistent)
OUTPUT_DIR = settings.VIDEO_OUTPUT_PATH
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _ken_burns(clip, zoom: float = 0.05):
    """
    Apply a slow zoom-in effect (Ken Burns) over the clip duration.
    For now, return the clip without effects due to OpenCV compatibility issues.

    Args:
        clip: ImageClip to apply effect to
        zoom: Maximum zoom factor (default 0.05 = 5% zoom)

    Returns:
        Modified clip with Ken Burns effect (currently disabled)
    """
    # Temporarily disable Ken Burns effect due to OpenCV compatibility issues
    # TODO: Fix OpenCV installation or use alternative approach
    return clip


def get_audio_duration(file_path: str) -> float:
    """Get duration of audio file using ffprobe."""
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', file_path
        ], capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"Could not get audio duration for {file_path}: {e}")
        return 0.0


def create_audio_concat_file(audio_files: list[str], output_file: str) -> str:
    """Create FFmpeg concat file for audio concatenation."""
    concat_file = output_file.replace('.wav', '_concat.txt')
    with open(concat_file, 'w') as f:
        for audio_file in audio_files:
            f.write(f"file '{audio_file}'\n")
    return concat_file


def concatenate_audio_files(audio_files: list[str], output_path: str) -> bool:
    """Concatenate audio files using FFmpeg for better quality."""
    if not audio_files:
        return False
    
    try:
        # Create concat file
        concat_file = create_audio_concat_file(audio_files, output_path)
        
        # Use FFmpeg to concatenate
        cmd = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"Audio concatenated successfully: {output_path}")
        
        # Clean up concat file
        os.remove(concat_file)
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Audio concatenation failed: {e}")
        return False


def compose_video_improved(scenes: list[dict], job_id: str) -> dict:
    """
    Compose final video from scene assets with improved audio-visual synchronization.
    
    This version:
    1. Properly concatenates audio files in sequence
    2. Creates video clips with correct timing
    3. Ensures audio and visual are perfectly synchronized

    Args:
        scenes: List of scene dicts with audio and visual paths
        job_id: Job identifier for output naming

    Returns:
        Dict with status, video_path, duration, and fps
    """
    try:
        from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, ColorClip
        
        # Step 1: Collect and validate all audio files
        audio_files = []
        valid_scenes = []
        
        for scene in scenes:
            audio_path = scene.get("audio", {}).get("path")
            visual_path = scene.get("visual", {}).get("path")
            
            # Check if files exist
            audio_exists = audio_path and os.path.exists(audio_path)
            visual_exists = visual_path and os.path.exists(visual_path)
            
            if not (audio_exists or visual_exists):
                logger.warning(
                    "Skipping scene with no valid files",
                    extra={"job_id": job_id, "scene_id": scene.get("scene_id")}
                )
                continue
            
            # Collect audio files for concatenation
            if audio_exists:
                audio_files.append(audio_path)
            
            valid_scenes.append({
                "scene_id": scene.get("scene_id"),
                "audio_path": audio_path if audio_exists else None,
                "visual_path": visual_path if visual_exists else None,
                "audio_duration": get_audio_duration(audio_path) if audio_exists else 0.0
            })
        
        if not valid_scenes:
            return {"status": "error", "error": "No valid scenes to compose"}
        
        # Step 2: Concatenate all audio files if we have multiple
        combined_audio_path = None
        if len(audio_files) > 1:
            # Create temporary combined audio file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_audio:
                combined_audio_path = tmp_audio.name
            
            if concatenate_audio_files(audio_files, combined_audio_path):
                logger.info(f"Audio concatenated: {len(audio_files)} files -> {combined_audio_path}")
            else:
                logger.warning("Audio concatenation failed, falling back to individual files")
                combined_audio_path = None
        elif len(audio_files) == 1:
            combined_audio_path = audio_files[0]
        
        # Step 3: Create video clips with proper timing
        clips = []
        
        for scene in valid_scenes:
            scene_id = scene["scene_id"]
            audio_path = scene["audio_path"]
            visual_path = scene["visual_path"]
            audio_duration = scene["audio_duration"]
            
            try:
                # Determine clip duration
                if audio_path:
                    # Use actual audio duration
                    clip_duration = audio_duration
                else:
                    # Default duration for visual-only clips
                    clip_duration = 5.0
                
                if clip_duration <= 0:
                    logger.warning(f"Invalid duration for scene {scene_id}, skipping")
                    continue
                
                # Create video clip
                if visual_path:
                    # Create image clip with Ken Burns effect
                    img_clip = ImageClip(visual_path, duration=clip_duration)
                    img_clip = _ken_burns(img_clip, zoom=0.06)
                    video_clip = img_clip
                else:
                    # Create black screen for audio-only clips
                    video_clip = ColorClip(size=(1920, 1080), color=(0, 0, 0), duration=clip_duration)
                
                # Add audio if available
                if audio_path:
                    audio_clip = AudioFileClip(audio_path)
                    # Ensure audio duration matches video duration
                    if audio_clip.duration != clip_duration:
                        logger.warning(
                            f"Audio duration mismatch for scene {scene_id}: "
                            f"audio={audio_clip.duration}s, expected={clip_duration}s"
                        )
                        # Trim or extend audio to match video duration
                        if audio_clip.duration > clip_duration:
                            audio_clip = audio_clip.subclip(0, clip_duration)
                        else:
                            # Extend audio by looping (simple approach)
                            loops_needed = int(clip_duration / audio_clip.duration) + 1
                            audio_clip = audio_clip.loop(loops_needed).subclip(0, clip_duration)
                    
                    # For MoviePy 1.0.3, use set_audio instead of with_audio
                    video_clip = video_clip.set_audio(audio_clip)
                
                clips.append(video_clip)
                
                logger.info(
                    "Scene clip created",
                    extra={
                        "job_id": job_id,
                        "scene_id": scene_id,
                        "duration": clip_duration,
                        "has_audio": bool(audio_path),
                        "has_visual": bool(visual_path)
                    }
                )
                
            except Exception as scene_error:
                logger.error(
                    "Failed to create scene clip",
                    extra={
                        "job_id": job_id,
                        "scene_id": scene_id,
                        "error": str(scene_error),
                        "error_type": type(scene_error).__name__
                    },
                    exc_info=True
                )
                continue
        
        if not clips:
            return {"status": "error", "error": "No valid clips created"}
        
        # Step 4: Concatenate video clips
        logger.info(
            "Concatenating video clips",
            extra={"job_id": job_id, "clip_count": len(clips)}
        )
        
        final_video = concatenate_videoclips(clips, method="compose")
        
        # Step 5: Write final video
        output_path = os.path.join(OUTPUT_DIR, f"video_{job_id}.mp4")
        logger.info("Writing final video", extra={"job_id": job_id, "output_path": output_path})
        
        final_video.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            logger=None,  # Suppress MoviePy's logger output
        )
        
        duration = final_video.duration
        
        # Step 6: Clean up
        for clip in clips:
            with contextlib.suppress(Exception):
                clip.close()
        
        with contextlib.suppress(Exception):
            final_video.close()
        
        # Clean up temporary combined audio file
        if combined_audio_path and combined_audio_path != audio_files[0]:
            with contextlib.suppress(Exception):
                os.remove(combined_audio_path)
        
        logger.info(
            "Video composition completed",
            extra={
                "job_id": job_id,
                "duration": duration,
                "output_path": output_path,
                "total_scenes": len(valid_scenes),
                "successful_clips": len(clips)
            }
        )
        
        return {
            "status": "success",
            "video_path": output_path,
            "duration": duration,
            "fps": 24,
            "total_scenes": len(valid_scenes),
            "successful_clips": len(clips)
        }
        
    except Exception as e:
        logger.error(
            "Video composition failed",
            extra={"job_id": job_id, "error": str(e)},
            exc_info=True
        )
        return {"status": "error", "error": str(e)}


# Keep the old function for backward compatibility
def compose_video_sync(scenes: list[dict], job_id: str) -> dict:
    """
    Legacy video composition function.
    Now calls the improved version.
    """
    logger.info("Using improved video composition", extra={"job_id": job_id})
    return compose_video_improved(scenes, job_id)
