import heapq
import random
import logging
from typing import Dict, Set
import asyncio
import redis.asyncio as redis

from app.asset_router import generate_visual_asset
from app.composer import Composer
from app.core.config import settings
from app.services.llm_service import generate_script
from app.services.tts_service import generate_audio
from app.utils.file import FileContext

logger = logging.getLogger(__name__)

# Global semaphore to limit concurrent jobs
_job_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_JOBS)

# Global set to track active jobs for cancellation support
_active_jobs: Set[str] = set()

# Simple in-memory priority queue for jobs (lower value = higher priority)
_job_priority_queue = []  # List of (priority, job_id, file)
_job_queue_lock = asyncio.Lock()

# Import redis_service with error handling
try:
    from app.services.redis_service import redis_service
    REDIS_AVAILABLE = True
except ImportError:
    redis_service = None
    REDIS_AVAILABLE = False


async def cancel_job(job_id: str) -> bool:
    """
    Cancel a running job if it exists.
    
    Args:
        job_id: Unique identifier for the job to cancel
        
    Returns:
        True if job was cancelled, False if job was not found or already completed
    """
    if job_id not in _active_jobs:
        logger.warning("Job cancellation requested but job not found", extra={"job_id": job_id})
        return False
    
    logger.info("Cancelling job", extra={"job_id": job_id})
    
    # Update job status to cancelled
    if REDIS_AVAILABLE and redis_service:
        try:
            await redis_service.set_job_status(
                job_id=job_id,
                status="cancelled",
                message="Job cancelled by user request",
                progress=0
            )
        except Exception as e:
            logger.error("Failed to update job status to cancelled", extra={
                "job_id": job_id,
                "error": str(e)
            })
    
    # Cancel all tasks associated with this job
    current_task = asyncio.current_task()
    for task in asyncio.all_tasks():
        if task != current_task and task.get_name().startswith(f"audio_{job_id}_") or task.get_name().startswith(f"visual_{job_id}_"):
            task.cancel()
    
    # Remove from active jobs
    _active_jobs.discard(job_id)
    
    return True


def get_active_jobs() -> Set[str]:
    """Get the set of currently active job IDs."""
    return _active_jobs.copy()


async def create_video_job(job_id: str, file: FileContext, priority: int = 10) -> None:
    """
    Core business logic for creating a video job.
    Orchestrates the generation of audio and visual assets in parallel.

    Args:
        job_id: Unique identifier for the video generation job
        file: File context containing the source content
    """
    # Acquire semaphore to limit concurrent jobs
    async with _job_semaphore:
        logger.info("Starting video job creation", extra={
            "job_id": job_id,
            "file": file.filename,
            "concurrent_jobs": len(_active_jobs)
        })

        # Add job to active jobs tracking
        _active_jobs.add(job_id)

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

        except asyncio.CancelledError:
            logger.info("Job was cancelled", extra={"job_id": job_id})
            # Set job status to cancelled if not already set
            if REDIS_AVAILABLE and redis_service:
                try:
                    await redis_service.set_job_status(
                        job_id=job_id,
                        status="cancelled",
                        message="Job was cancelled during execution",
                        progress=0
                    )
                except Exception as redis_error:
                    logger.error("Failed to update job status to cancelled", extra={
                        "job_id": job_id,
                        "redis_error": str(redis_error)
                    })
            raise

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

        finally:
            # Always remove job from active jobs tracking
            _active_jobs.discard(job_id)


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

        # Generate audio asset with retry
        audio_data = await retry_async(generate_audio, scene)

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

        # Generate visual asset with retry
        visual_data = await retry_async(generate_visual_asset, scene, job_id)

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


# Retry utility with exponential backoff
async def retry_async(fn, *args, retries=3, base_delay=1.0, max_delay=10.0, **kwargs):
    for attempt in range(retries):
        try:
            return await fn(*args, **kwargs)
        except Exception as e:
            if attempt == retries - 1:
                raise
            delay = min(base_delay * (2 ** attempt) + random.uniform(0, 0.5), max_delay)
            logger.warning(f"Retry {attempt+1}/{retries} after error: {e}. Backing off for {delay:.2f}s")
            await asyncio.sleep(delay)


async def enqueue_job(job_id: str, file: FileContext, priority: int = 10):
    async with _job_queue_lock:
        heapq.heappush(_job_priority_queue, (priority, job_id, file))


async def dequeue_job():
    async with _job_queue_lock:
        if _job_priority_queue:
            return heapq.heappop(_job_priority_queue)
        return None


async def job_queue_worker():
    while True:
        job = await dequeue_job()
        if job:
            priority, job_id, file = job
            await create_video_job(job_id, file)
        else:
            await asyncio.sleep(0.5)  # Wait before checking again
