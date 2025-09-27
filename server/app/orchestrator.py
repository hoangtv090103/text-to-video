import logging
from typing import Dict
import asyncio

from app.asset_router import generate_visual_asset, exponential_backoff_retry
from app.composer import Composer
from app.services.job_service import job_service
from app.services.llm_service import generate_script
from app.services.tts_service import generate_audio
from app.utils.file import FileContext

logger = logging.getLogger(__name__)

composer = Composer()


async def create_video_job(job_id: str, file: FileContext) -> None:
    """Orchestrate video generation for a job."""
    logger.info("Starting video job creation", extra={"job_id": job_id, "file": file.filename})

    try:
        await job_service.initialize_job(job_id, message="Initializing video generation", progress=5)

        if await job_service.is_job_cancelled(job_id):
            logger.info("Job was cancelled before processing started", extra={"job_id": job_id})
            return

        await job_service.update_job_progress(job_id, 15, "Generating script from source text")

        @exponential_backoff_retry(max_retries=3, base_delay=2.0)
        async def generate_script_with_retry():
            return await generate_script(file)

        script_scenes = await generate_script_with_retry()
        await job_service.update_job_progress(job_id, 25, f"Generated script with {len(script_scenes)} scenes")

        if await job_service.is_job_cancelled(job_id):
            logger.info("Job was cancelled after script generation", extra={"job_id": job_id})
            return

        tasks = []
        for scene in script_scenes:
            if await job_service.is_job_cancelled(job_id):
                logger.info("Job was cancelled during scene processing", extra={"job_id": job_id})
                break

            scene_id = scene["id"]
            audio_task = asyncio.create_task(_process_audio_asset(job_id, scene), name=f"audio_{job_id}_{scene_id}")
            visual_task = asyncio.create_task(_process_visual_asset(job_id, scene), name=f"visual_{job_id}_{scene_id}")
            tasks.extend([audio_task, visual_task])

        if not tasks:
            await job_service.set_job_status(job_id, "cancelled", "Job cancelled before processing assets")
            return

        await job_service.update_job_progress(job_id, 50, "Generating audio and visual assets")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        if await job_service.is_job_cancelled(job_id):
            logger.info("Job was cancelled after asset generation", extra={"job_id": job_id})
            return

        job_data = await job_service.get_job_status(job_id) or {}
        await job_service.update_job_metadata(job_id, segments=job_data.get("segments", {}))

        successful_tasks = sum(1 for result in results if not isinstance(result, Exception))
        failed_tasks = len(results) - successful_tasks

        logger.info("Video job processing completed", extra={
            "job_id": job_id,
            "total_tasks": len(tasks),
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks
        })

        if failed_tasks > 0:
            await job_service.set_job_status(
                job_id,
                "completed_with_errors",
                f"Completed with {failed_tasks} failed tasks out of {len(tasks)}",
                progress=100
            )
        else:
            await job_service.set_job_status(
                job_id,
                "completed",
                "Video generation completed successfully",
                progress=100
            )

    except Exception as exc:
        logger.error("Video job creation failed", extra={"job_id": job_id, "error": str(exc)})
        await job_service.set_job_status(
            job_id,
            "failed",
            f"Job failed: {str(exc)}",
            progress=0
        )
        raise


async def _process_audio_asset(job_id: str, scene: Dict) -> None:
    scene_id = scene["id"]

    if await job_service.is_job_cancelled(job_id):
        logger.info("Audio processing cancelled", extra={"job_id": job_id, "scene_id": scene_id})
        return

    try:
        logger.debug("Starting audio processing", extra={"job_id": job_id, "scene_id": scene_id})
        audio_data = await generate_audio(scene)

        if await job_service.is_job_cancelled(job_id):
            logger.info("Audio processing completed but job cancelled", extra={"job_id": job_id, "scene_id": scene_id})
            return

        segment_state = await composer.handle_asset_completion(job_id, scene_id, "audio", audio_data)
        await job_service.update_segment(job_id, scene_id, segment_state)

    except Exception as exc:
        logger.error("Audio processing failed", extra={
            "job_id": job_id,
            "scene_id": scene_id,
            "error": str(exc)
        })
        failure_data = {
            "path": "",
            "duration": 0,
            "status": "failed",
            "error": str(exc)
        }
        await composer.handle_asset_completion(job_id, scene_id, "audio", failure_data)


async def _process_visual_asset(job_id: str, scene: Dict) -> None:
    scene_id = scene["id"]

    if await job_service.is_job_cancelled(job_id):
        logger.info("Visual processing cancelled", extra={"job_id": job_id, "scene_id": scene_id})
        return

    try:
        logger.debug("Starting visual processing", extra={"job_id": job_id, "scene_id": scene_id})
        visual_data = await generate_visual_asset(scene, job_id)

        if await job_service.is_job_cancelled(job_id):
            logger.info("Visual processing completed but job cancelled", extra={"job_id": job_id, "scene_id": scene_id})
            return

        segment_state = await composer.handle_asset_completion(job_id, scene_id, "visual", visual_data)
        await job_service.update_segment(job_id, scene_id, segment_state)

    except Exception as exc:
        logger.error("Visual processing failed", extra={
            "job_id": job_id,
            "scene_id": scene_id,
            "error": str(exc)
        })
        failure_data = {
            "path": "",
            "status": "failed",
            "visual_type": scene.get("visual_type", "unknown"),
            "error": str(exc)
        }
        await composer.handle_asset_completion(job_id, scene_id, "visual", failure_data)
