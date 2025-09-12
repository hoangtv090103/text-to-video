import os
import logging
from typing import Dict, List, Optional
from moviepy import (
    VideoClip, AudioFileClip, ImageClip, CompositeVideoClip,
    concatenate_videoclips, ColorClip
)
import time

logger = logging.getLogger(__name__)

# Video output configuration
VIDEO_OUTPUT_PATH = os.environ.get("VIDEO_OUTPUT_PATH", "/tmp/videos")
os.makedirs(VIDEO_OUTPUT_PATH, exist_ok=True)

# Video settings
DEFAULT_VIDEO_WIDTH = 1920
DEFAULT_VIDEO_HEIGHT = 1080
DEFAULT_FPS = 30
DEFAULT_BACKGROUND_COLOR = (255, 255, 255)  # White background


class VideoComposerSync:
    """
    Synchronous video composer that combines audio and visual assets into final video.
    """

    def __init__(self):
        self.video_width = DEFAULT_VIDEO_WIDTH
        self.video_height = DEFAULT_VIDEO_HEIGHT
        self.fps = DEFAULT_FPS
        self.background_color = DEFAULT_BACKGROUND_COLOR

    def create_video_from_scenes(self, scenes_with_assets: List[Dict], job_id: str) -> Dict:
        """
        Create final video from scenes with audio and visual assets.

        Args:
            scenes_with_assets: List of scenes with their audio and visual assets
            job_id: Job identifier for output naming

        Returns:
            Dictionary with video information
        """
        logger.info("Starting video composition", extra={
            "job_id": job_id,
            "total_scenes": len(scenes_with_assets)
        })

        start_time = time.time()
        output_file = os.path.join(VIDEO_OUTPUT_PATH, f"job_{job_id}_final_video.mp4")

        try:
            # Filter out scenes with missing assets
            valid_scenes = self._filter_valid_scenes(scenes_with_assets)

            if not valid_scenes:
                raise Exception("No valid scenes with both audio and visual assets found")

            # Create video clips for each scene
            scene_clips = []
            total_duration = 0

            for i, scene in enumerate(valid_scenes):
                scene_id = scene.get("scene_id", i + 1)
                audio_data = scene.get("audio")
                visual_data = scene.get("visual")

                logger.info("Processing scene for video", extra={
                    "job_id": job_id,
                    "scene_id": scene_id
                })

                # Create scene clip
                scene_clip = self._create_scene_clip(
                    audio_data=audio_data or {},
                    visual_data=visual_data or {},
                    scene_id=scene_id,
                    job_id=job_id
                )

                if scene_clip:
                    scene_clips.append(scene_clip)
                    total_duration += scene_clip.duration
                    logger.info("Scene clip created successfully", extra={
                        "job_id": job_id,
                        "scene_id": scene_id,
                        "duration": scene_clip.duration
                    })
                else:
                    logger.warning("Failed to create scene clip", extra={
                        "job_id": job_id,
                        "scene_id": scene_id
                    })

            if not scene_clips:
                raise Exception("No valid scene clips could be created")

            # Concatenate all scene clips
            logger.info("Concatenating scene clips", extra={
                "job_id": job_id,
                "clip_count": len(scene_clips),
                "total_duration": total_duration
            })

            final_video = concatenate_videoclips(scene_clips, method="compose")

            # Write the final video
            logger.info("Writing final video to file", extra={
                "job_id": job_id,
                "output_file": output_file
            })

            final_video.write_videofile(
                output_file,
                fps=self.fps,
                audio_codec='aac',
                codec='libx264',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                logger=None  # Disable moviepy logging
            )

            # Clean up clips
            final_video.close()
            for clip in scene_clips:
                clip.close()

            end_time = time.time()
            composition_time = end_time - start_time

            # Get file size
            file_size = os.path.getsize(output_file) if os.path.exists(output_file) else 0

            logger.info("Video composition completed successfully", extra={
                "job_id": job_id,
                "output_file": output_file,
                "duration": total_duration,
                "file_size": file_size,
                "composition_time": f"{composition_time:.2f}s"
            })

            return {
                "status": "success",
                "video_path": output_file,
                "duration": total_duration,
                "file_size": file_size,
                "composition_time": composition_time,
                "scenes_processed": len(valid_scenes),
                "video_format": "mp4",
                "resolution": f"{self.video_width}x{self.video_height}",
                "fps": self.fps
            }

        except Exception as e:
            end_time = time.time()
            composition_time = end_time - start_time

            logger.error("Video composition failed", extra={
                "job_id": job_id,
                "error": str(e),
                "composition_time": f"{composition_time:.2f}s"
            })

            return {
                "status": "failed",
                "error": str(e),
                "composition_time": composition_time
            }

    def _filter_valid_scenes(self, scenes_with_assets: List[Dict]) -> List[Dict]:
        """
        Filter scenes that have both valid audio and visual assets.

        Args:
            scenes_with_assets: List of scenes with assets

        Returns:
            List of valid scenes
        """
        valid_scenes = []

        for scene in scenes_with_assets:
            audio_data = scene.get("audio")
            visual_data = scene.get("visual")

            # Check if both audio and visual assets exist and are valid
            audio_valid = (
                audio_data and
                audio_data.get("status") == "success" and
                audio_data.get("path") and
                os.path.exists(audio_data.get("path", ""))
            )

            visual_valid = (
                visual_data and
                visual_data.get("status") == "success" and
                visual_data.get("path") and
                os.path.exists(visual_data.get("path", ""))
            )

            if audio_valid and visual_valid:
                valid_scenes.append(scene)
            else:
                logger.warning("Scene has invalid assets", extra={
                    "scene_id": scene.get("scene_id"),
                    "audio_valid": audio_valid,
                    "visual_valid": visual_valid
                })

        return valid_scenes

    def _create_scene_clip(
        self,
        audio_data: Dict,
        visual_data: Dict,
        scene_id: int,
        job_id: str
    ) -> Optional['VideoClip']:
        """
        Create a video clip for a single scene by combining audio and visual.

        Args:
            audio_data: Audio asset data
            visual_data: Visual asset data
            scene_id: Scene identifier
            job_id: Job identifier

        Returns:
            VideoClip or None if creation fails
        """
        try:
            # Load audio
            audio_path = audio_data.get("path")
            audio_clip = AudioFileClip(audio_path)
            audio_duration = audio_clip.duration

            logger.debug("Audio loaded", extra={
                "job_id": job_id,
                "scene_id": scene_id,
                "audio_duration": audio_duration
            })

            # Load visual (image)
            visual_path = visual_data.get("path")

            # Create image clip with audio duration
            image_clip = ImageClip(visual_path, duration=audio_duration)

            # Resize image to fit video dimensions while maintaining aspect ratio
            image_clip = image_clip.resized(height=self.video_height)

            # If image is wider than video, crop it
            if image_clip.w > self.video_width:
                image_clip = image_clip.resized(width=self.video_width)

            # Center the image on a background
            background = ColorClip(
                size=(self.video_width, self.video_height),
                color=self.background_color,
                duration=audio_duration
            )

            # Composite image on background (centered)
            video_clip = CompositeVideoClip([
                background,
                image_clip.with_position('center')
            ])

            # Set audio
            final_clip = video_clip.with_audio(audio_clip)

            logger.debug("Scene clip created", extra={
                "job_id": job_id,
                "scene_id": scene_id,
                "duration": final_clip.duration
            })

            return final_clip

        except Exception as e:
            logger.error("Failed to create scene clip", extra={
                "job_id": job_id,
                "scene_id": scene_id,
                "error": str(e)
            })
            return None


# Global instance
video_composer = VideoComposerSync()


def compose_video_sync(scenes_with_assets: List[Dict], job_id: str) -> Dict:
    """
    Convenience function for video composition.

    Args:
        scenes_with_assets: List of scenes with audio and visual assets
        job_id: Job identifier

    Returns:
        Video composition result
    """
    return video_composer.create_video_from_scenes(scenes_with_assets, job_id)
