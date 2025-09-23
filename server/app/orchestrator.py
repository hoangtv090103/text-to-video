import logging
from typing import Dict
import asyncio
import redis.asyncio as redis

from app.asset_router import generate_visual_asset
from app.composer import Composer
from app.core.config import settings
from app.services.llm_service import generate_script
from app.services.tts_service import generate_audio
from app.utils.file import FileContext

logger = logging.getLogger(__name__)

# Import redis_service with error handling
try:
    from app.services.redis_service import redis_service
    REDIS_AVAILABLE = True
except ImportError:
    redis_service = None
    REDIS_AVAILABLE = False


async def create_video_job(job_id: str, file: FileContext) -> None:
    """
    Core business logic for creating a video job.
    Orchestrates the generation of audio and visual assets in parallel.

    Args:
        job_id: Unique identifier for the video generation job
        file: File context containing the source content
    """
    logger.info("Starting video job creation", extra={
        "job_id": job_id,
        "file": file.filename
    })

    try:
        # Set initial job status
        if REDIS_AVAILABLE and redis_service:
            await redis_service.set_job_status(
                job_id=job_id,
                status="processing",
                message="Initializing video generation",
                progress=5
            )

        # Step 1: Generate script from source text using LLM service
        if REDIS_AVAILABLE and redis_service:
            await redis_service.update_job_progress(job_id, 15, "Generating script from source text")

        script_scenes = await generate_script(file)

        logger.info("Script generated successfully", extra={
            "job_id": job_id,
            "total_scenes": len(script_scenes)
        })

        # Update progress after script generation
        if REDIS_AVAILABLE and redis_service:
            await redis_service.update_job_progress(job_id, 25, f"Generated script with {len(script_scenes)} scenes")

        # # Step 2: Initialize Redis connection and composer
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=False  # Keep as bytes for consistent handling
        )

        composer = Composer(redis_client)

        # Step 3: Process each scene with parallel audio and visual generation
        if REDIS_AVAILABLE and redis_service:
            await redis_service.update_job_progress(job_id, 30, "Starting parallel asset generation")

        tasks = []

        for scene in script_scenes:
            scene_id = scene["id"]

            # Create audio generation task
            audio_task = asyncio.create_task(
                _process_audio_asset(job_id, scene, composer),
                name=f"audio_{job_id}_{scene_id}"
            )

            # Create visual generation task
            visual_task = asyncio.create_task(
                _process_visual_asset(job_id, scene, composer),
                name=f"visual_{job_id}_{scene_id}"
            )

            tasks.extend([audio_task, visual_task])

        # Step 4: Wait for all tasks to complete
        logger.info("Starting parallel asset generation", extra={
            "job_id": job_id,
            "total_tasks": len(tasks)
        })

        # Update progress during asset generation
        if REDIS_AVAILABLE and redis_service:
            await redis_service.update_job_progress(job_id, 50, "Generating audio and visual assets")

        # Use asyncio.gather with return_exceptions=True to handle individual failures
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log completion statistics
        successful_tasks = sum(1 for result in results if not isinstance(result, Exception))
        failed_tasks = len(results) - successful_tasks

        logger.info("Video job processing completed", extra={
            "job_id": job_id,
            "total_tasks": len(tasks),
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks
        })

        if failed_tasks > 0:
            # Some tasks failed
            if REDIS_AVAILABLE and redis_service:
                await redis_service.set_job_status(
                    job_id=job_id,
                    status="completed_with_errors",
                    message=f"Completed with {failed_tasks} failed tasks out of {len(tasks)}",
                    progress=100,
                    metadata={"successful_tasks": successful_tasks, "failed_tasks": failed_tasks}
                )
        else:
            # All tasks completed successfully
            if REDIS_AVAILABLE and redis_service:
                await redis_service.set_job_status(
                    job_id=job_id,
                    status="completed",
                    message="Video generation completed successfully",
                    progress=100,
                    metadata={"total_scenes": len(script_scenes), "total_tasks": len(tasks)}
                )

        # Close Redis connection
        await redis_client.close()

    except Exception as e:
        logger.error("Video job creation failed", extra={
            "job_id": job_id,
            "error": str(e)
        })

        # Set job status to failed
        if REDIS_AVAILABLE and redis_service:
            try:
                await redis_service.set_job_status(
                    job_id=job_id,
                    status="failed",
                    message=f"Job failed: {str(e)}",
                    progress=0
                )
            except Exception as redis_error:
                logger.error("Failed to update job status to failed", extra={
                    "job_id": job_id,
                    "redis_error": str(redis_error)
                })

        raise


async def _process_audio_asset(job_id: str, scene: Dict, composer: Composer) -> None:
    """
    Process audio asset generation for a scene.

    Args:
        job_id: Unique identifier for the video generation job
        scene: Scene data dictionary
        composer: Composer instance for state management
    """
    scene_id = scene["id"]

    try:
        logger.debug("Starting audio processing", extra={
            "job_id": job_id,
            "scene_id": scene_id
        })

        # Generate audio asset
        audio_data = await generate_audio(scene)

        # Report completion to composer
        await composer.handle_asset_completion(
            job_id=job_id,
            segment_id=scene_id,
            asset_type="audio",
            asset_data=audio_data
        )

    except Exception as e:
        logger.error("Audio processing failed", extra={
            "job_id": job_id,
            "scene_id": scene_id,
            "error": str(e)
        })

        # Report failure to composer
        await composer.handle_asset_completion(
            job_id=job_id,
            segment_id=scene_id,
            asset_type="audio",
            asset_data={
                "path": "",
                "duration": 0,
                "status": "failed",
                "error": str(e)
            }
        )


async def _process_visual_asset(job_id: str, scene: Dict, composer: Composer) -> None:
    """
    Process visual asset generation for a scene.

    Args:
        job_id: Unique identifier for the video generation job
        scene: Scene data dictionary
        composer: Composer instance for state management
    """
    scene_id = scene["id"]

    try:
        logger.debug("Starting visual processing", extra={
            "job_id": job_id,
            "scene_id": scene_id
        })

        # Generate visual asset (includes retry logic and error handling)
        visual_data = await generate_visual_asset(scene, job_id)

        # Report completion to composer
        await composer.handle_asset_completion(
            job_id=job_id,
            segment_id=scene_id,
            asset_type="visual",
            asset_data=visual_data
        )

    except Exception as e:
        logger.error("Visual processing failed", extra={
            "job_id": job_id,
            "scene_id": scene_id,
            "error": str(e)
        })

        # Report failure to composer
        await composer.handle_asset_completion(
            job_id=job_id,
            segment_id=scene_id,
            asset_type="visual",
            asset_data={
                "path": "",
                "status": "failed",
                "visual_type": scene.get("visual_type", "unknown"),
                "error": str(e)
            }
        )
