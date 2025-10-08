import os
import logging
from typing import Dict, List, Optional
from moviepy import (
    VideoClip, AudioFileClip, ImageClip, CompositeVideoClip,
    concatenate_videoclips, ColorClip
)
import time

from app.core.config import settings

logger = logging.getLogger(__name__)

# Video output configuration
VIDEO_OUTPUT_PATH = settings.VIDEO_OUTPUT_PATH
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
            # Validate input data
            if not scenes_with_assets:
                raise ValueError("No scenes provided for video composition")

            # Filter and validate scenes with missing assets
            valid_scenes = self._filter_valid_scenes(scenes_with_assets)

            if not valid_scenes:
                raise ValueError("No valid scenes with both audio and visual assets found")

            # Sort scenes by scene_id to ensure correct order
            valid_scenes.sort(key=lambda x: x.get("scene_id", 0))

            # Create video clips for each scene with audio-visual sync
            scene_clips = []
            total_duration = 0
            processed_scenes = 0

            for i, scene in enumerate(valid_scenes):
                scene_id = scene.get("scene_id", i + 1)
                audio_data = scene.get("audio", {})
                visual_data = scene.get("visual", {})

                logger.info("Processing scene for video", extra={
                    "job_id": job_id,
                    "scene_id": scene_id,
                    "scene_index": i + 1,
                    "total_scenes": len(valid_scenes)
                })

                # Validate scene data
                self._validate_scene_data(audio_data, visual_data, scene_id)

                # Create scene clip with proper audio-visual sync
                scene_clip = self._create_scene_clip(
                    audio_data=audio_data,
                    visual_data=visual_data,
                    scene_id=scene_id,
                    job_id=job_id
                )

                if scene_clip:
                    scene_clips.append(scene_clip)
                    scene_duration = scene_clip.duration
                    total_duration += scene_duration
                    processed_scenes += 1

                    logger.info("Scene clip created successfully", extra={
                        "job_id": job_id,
                        "scene_id": scene_id,
                        "duration": scene_duration,
                        "total_duration": total_duration
                    })
                else:
                    logger.warning("Failed to create scene clip", extra={
                        "job_id": job_id,
                        "scene_id": scene_id,
                        "audio_path": audio_data.get("path", "None"),
                        "visual_path": visual_data.get("path", "None")
                    })

            if not scene_clips:
                raise ValueError("No valid scene clips could be created")

            # Ensure minimum video duration
            if total_duration < 1.0:
                logger.warning("Video duration too short, adding padding", extra={
                    "job_id": job_id,
                    "total_duration": total_duration
                })
                total_duration = max(total_duration, 1.0)

            # Concatenate all scene clips with smooth transitions
            logger.info("Concatenating scene clips", extra={
                "job_id": job_id,
                "clip_count": len(scene_clips),
                "total_duration": total_duration,
                "processed_scenes": processed_scenes
            })

            final_video = concatenate_videoclips(scene_clips, method="compose")

            # Write the final video with optimized settings
            logger.info("Writing final video to file", extra={
                "job_id": job_id,
                "output_file": output_file,
                "fps": self.fps,
                "resolution": f"{self.video_width}x{self.video_height}"
            })

            # Use optimized video settings
            final_video.write_videofile(
                output_file,
                fps=self.fps,
                audio_codec='aac',
                codec='libx264',
                preset='fast',  # Faster encoding
                bitrate='2000k',  # Set bitrate for consistent quality
                temp_audiofile=os.path.join(VIDEO_OUTPUT_PATH, f'temp_audio_{job_id}.m4a'),
                remove_temp=True,
                logger=None,  # Disable moviepy logging
                verbose=False
            )

            # Clean up clips to free memory
            final_video.close()
            for clip in scene_clips:
                clip.close()

            end_time = time.time()
            composition_time = end_time - start_time

            # Get file information
            file_size = os.path.getsize(output_file) if os.path.exists(output_file) else 0
            file_size_mb = file_size / (1024 * 1024)

            logger.info("Video composition completed successfully", extra={
                "job_id": job_id,
                "output_file": output_file,
                "duration": total_duration,
                "file_size_mb": f"{file_size_mb:.2f}",
                "composition_time": f"{composition_time:.2f}s",
                "scenes_processed": processed_scenes
            })

            return {
                "status": "success",
                "video_path": output_file,
                "duration": total_duration,
                "file_size": file_size,
                "file_size_mb": file_size_mb,
                "composition_time": composition_time,
                "scenes_processed": processed_scenes,
                "total_scenes": len(scenes_with_assets),
                "video_format": "mp4",
                "resolution": f"{self.video_width}x{self.video_height}",
                "fps": self.fps,
                "bitrate": "2000k"
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

    def _validate_scene_data(self, audio_data: Dict, visual_data: Dict, scene_id: int) -> None:
        """
        Validate scene data before creating video clip.

        Args:
            audio_data: Audio asset data
            visual_data: Visual asset data
            scene_id: Scene identifier

        Raises:
            ValueError: If validation fails
        """
        # Validate audio data
        if not audio_data:
            raise ValueError(f"Scene {scene_id}: No audio data provided")

        if audio_data.get("status") != "success":
            raise ValueError(f"Scene {scene_id}: Audio generation failed - {audio_data.get('error', 'Unknown error')}")

        audio_path = audio_data.get("path")
        if not audio_path or not os.path.exists(audio_path):
            raise ValueError(f"Scene {scene_id}: Audio file not found at {audio_path}")

        # Validate visual data
        if not visual_data:
            raise ValueError(f"Scene {scene_id}: No visual data provided")

        if visual_data.get("status") not in ["success", "failed_with_placeholder"]:
            raise ValueError(f"Scene {scene_id}: Visual generation failed - {visual_data.get('error', 'Unknown error')}")

        visual_path = visual_data.get("path")
        if not visual_path or not os.path.exists(visual_path):
            raise ValueError(f"Scene {scene_id}: Visual file not found at {visual_path}")

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
            scene_id = scene.get("scene_id", "unknown")
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
                visual_data.get("status") in ["success", "failed_with_placeholder"] and
                visual_data.get("path") and
                os.path.exists(visual_data.get("path", ""))
            )

            if audio_valid and visual_valid:
                valid_scenes.append(scene)
            else:
                logger.warning("Scene has invalid assets", extra={
                    "scene_id": scene_id,
                    "audio_valid": audio_valid,
                    "visual_valid": visual_valid,
                    "audio_path": audio_data.get("path") if audio_data else "None",
                    "visual_path": visual_data.get("path") if visual_data else "None"
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
        Create a video clip for a single scene with proper audio-visual sync.

        Args:
            audio_data: Audio asset data
            visual_data: Visual asset data
            scene_id: Scene identifier
            job_id: Job identifier

        Returns:
            VideoClip or None if creation fails
        """
        try:
            # Load audio with error handling
            audio_path = audio_data.get("path")
            if not audio_path:
                raise ValueError("No audio path provided")

            audio_clip = AudioFileClip(audio_path)
            audio_duration = audio_clip.duration

            # Ensure minimum audio duration
            if audio_duration < 0.1:
                logger.warning("Audio duration too short", extra={
                    "job_id": job_id,
                    "scene_id": scene_id,
                    "audio_duration": audio_duration
                })
                audio_duration = 0.1  # Minimum 0.1 seconds

            logger.debug("Audio loaded", extra={
                "job_id": job_id,
                "scene_id": scene_id,
                "audio_duration": audio_duration,
                "audio_path": audio_path
            })

            # Load visual (image) with error handling
            visual_path = visual_data.get("path")
            if not visual_path:
                raise ValueError("No visual path provided")

            # Create image clip with exact audio duration
            image_clip = ImageClip(visual_path, duration=audio_duration)

            # Get original image dimensions
            original_width, original_height = image_clip.size

            # Calculate scaling to fit video dimensions while maintaining aspect ratio
            width_ratio = self.video_width / original_width
            height_ratio = self.video_height / original_height
            scale_factor = min(width_ratio, height_ratio)

            # Resize image
            new_width = int(original_width * scale_factor)
            new_height = int(original_height * scale_factor)
            image_clip = image_clip.resized((new_width, new_height))

            # Create background
            background = ColorClip(
                size=(self.video_width, self.video_height),
                color=self.background_color,
                duration=audio_duration
            )

            # Center the image on background
            x_offset = (self.video_width - new_width) // 2
            y_offset = (self.video_height - new_height) // 2

            # Composite image on background
            video_clip = CompositeVideoClip([
                background,
                image_clip.with_position((x_offset, y_offset))
            ])

            # Set audio with proper sync
            final_clip = video_clip.with_audio(audio_clip)

            # Verify final clip duration matches audio
            final_duration = final_clip.duration
            if abs(final_duration - audio_duration) > 0.1:  # Allow 0.1s tolerance
                logger.warning("Audio-visual duration mismatch", extra={
                    "job_id": job_id,
                    "scene_id": scene_id,
                    "audio_duration": audio_duration,
                    "video_duration": final_duration
                })

            logger.debug("Scene clip created successfully", extra={
                "job_id": job_id,
                "scene_id": scene_id,
                "duration": final_duration,
                "audio_duration": audio_duration,
                "image_size": f"{new_width}x{new_height}",
                "position": f"({x_offset}, {y_offset})"
            })

            return final_clip

        except Exception as e:
            logger.error("Failed to create scene clip", extra={
                "job_id": job_id,
                "scene_id": scene_id,
                "error": str(e),
                "audio_path": audio_data.get("path", "None"),
                "visual_path": visual_data.get("path", "None")
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
