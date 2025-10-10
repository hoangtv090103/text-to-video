import asyncio
import logging

from app.asset_router import exponential_backoff_retry, generate_visual_asset
from app.composer import Composer
from app.services.job_service import job_service
from app.services.llm_service import generate_script
from app.services.tts_service import generate_audio
from app.utils.file import FileContext

logger = logging.getLogger(__name__)

composer = Composer()


async def create_video_job(job_id: str, file: FileContext) -> None:
    """Orchestrate video generation for a job."""
    logger.info("Starting video job creation", extra={"job_id": job_id, "uploaded_file": file.filename})

    try:
        # Validate file context
        if not file or not file.contents:
            raise ValueError("Invalid file context: file contents are empty")

        if not file.filename:
            raise ValueError("Invalid file context: filename is missing")

        await job_service.initialize_job(
            job_id, message="Initializing video generation", progress=5
        )

        # Health check before processing
        logger.info("Performing health checks before processing", extra={"job_id": job_id})
        from app.services.llm_service import check_llm_health
        from app.main import check_tts_health

        tts_healthy = await check_tts_health()
        llm_healthy = await check_llm_health()

        if not tts_healthy:
            logger.warning("TTS service not healthy, job may fail", extra={"job_id": job_id})

        if not llm_healthy:
            logger.warning("LLM service not healthy, job may fail", extra={"job_id": job_id})

        if await job_service.is_job_cancelled(job_id):
            logger.info("Job was cancelled before processing started", extra={"job_id": job_id})
            return

        await job_service.update_job_progress(job_id, 15, "Generating script from source text")

        @exponential_backoff_retry(max_retries=3, base_delay=2.0)
        async def generate_script_with_retry():
            return await generate_script(file)

        script_scenes = await generate_script_with_retry()
        await job_service.update_job_progress(
            job_id, 25, f"Generated script with {len(script_scenes)} scenes"
        )

        if await job_service.is_job_cancelled(job_id):
            logger.info("Job was cancelled after script generation", extra={"job_id": job_id})
            return

        tasks = []
        for scene in script_scenes:
            if await job_service.is_job_cancelled(job_id):
                logger.info("Job was cancelled during scene processing", extra={"job_id": job_id})
                break

            scene_id = scene["id"]
            audio_task = asyncio.create_task(
                _process_audio_asset(job_id, scene), name=f"audio_{job_id}_{scene_id}"
            )
            visual_task = asyncio.create_task(
                _process_visual_asset(job_id, scene), name=f"visual_{job_id}_{scene_id}"
            )
            tasks.extend([audio_task, visual_task])

        if not tasks:
            await job_service.set_job_status(
                job_id, "cancelled", "Job cancelled before processing assets"
            )
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

        logger.info(
            "Video job processing completed",
            extra={
                "job_id": job_id,
                "total_tasks": len(tasks),
                "successful_tasks": successful_tasks,
                "failed_tasks": failed_tasks,
            },
        )

        # Try to compose video if we have valid scenes
        video_result = None
        try:
            from app.services.video_composer_sync import compose_video_sync

            # Get segments data for video composition
            segments = job_data.get("segments", {})
            scenes_with_assets = []

            for segment_id, segment_data in segments.items():
                if (
                    segment_data.get("audio_status") == "success"
                    and segment_data.get("visual_status") == "success"
                ):
                    scenes_with_assets.append(
                        {
                            "scene_id": int(segment_id),
                            "audio": {
                                "path": segment_data.get("audio_path"),
                                "duration": segment_data.get("audio_duration", 0),
                            },
                            "visual": {
                                "path": segment_data.get("visual_path"),
                                "visual_type": segment_data.get("visual_type", "slide"),
                            },
                        }
                    )

            if scenes_with_assets:
                logger.info(
                    "Starting video composition",
                    extra={"job_id": job_id, "scenes_count": len(scenes_with_assets)},
                )

                video_result = compose_video_sync(scenes_with_assets, job_id)

                if video_result.get("status") == "success":
                    logger.info(
                        "Video composition completed successfully",
                        extra={
                            "job_id": job_id,
                            "video_path": video_result.get("video_path"),
                            "duration": video_result.get("duration"),
                        },
                    )
                else:
                    logger.error(
                        "Video composition failed",
                        extra={"job_id": job_id, "error": video_result.get("error")},
                    )
            else:
                logger.warning("No valid scenes for video composition", extra={"job_id": job_id})

        except ImportError as import_error:
            logger.error(
                "Video composition module not available",
                extra={
                    "job_id": job_id,
                    "error": f"Composition module not found: {str(import_error)}",
                },
            )
        except Exception as composition_error:
            logger.error(
                "Video composition failed",
                extra={"job_id": job_id, "error": str(composition_error)},
            )

        # Prepare final result
        final_result = {
            "job_id": job_id,
            "status": "completed" if failed_tasks == 0 else "completed_with_errors",
            "message": "Video generation completed successfully"
            if failed_tasks == 0
            else f"Completed with {failed_tasks} failed tasks",
            "total_scenes": len(script_scenes),
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
            "scenes": list(job_data.get("segments", {}).values()),
            "script_scenes": script_scenes,
        }

        if video_result:
            final_result["video"] = video_result

        # Save result to job service
        await job_service.set_job_result(job_id, final_result)

        if failed_tasks > 0:
            await job_service.set_job_status(
                job_id,
                "completed_with_errors",
                f"Completed with {failed_tasks} failed tasks out of {len(tasks)}",
                progress=100,
            )
        else:
            await job_service.set_job_status(
                job_id, "completed", "Video generation completed successfully", progress=100
            )

    except Exception as exc:
        logger.error(
            "Video job creation failed",
            extra={"job_id": job_id, "error": str(exc), "error_type": type(exc).__name__},
            exc_info=True,
        )
        # Set job status to failed and don't re-raise to prevent background task crash
        try:
            await job_service.set_job_status(
                job_id, "failed", f"Job failed: {type(exc).__name__}: {str(exc)}", progress=0
            )
        except Exception as status_error:
            logger.error(
                "Failed to update job status after error",
                extra={"job_id": job_id, "error": str(status_error)},
            )


async def _process_audio_asset(job_id: str, scene: dict) -> None:
    scene_id = scene["id"]

    if await job_service.is_job_cancelled(job_id):
        logger.info("Audio processing cancelled", extra={"job_id": job_id, "scene_id": scene_id})
        return

    try:
        logger.debug("Starting audio processing", extra={"job_id": job_id, "scene_id": scene_id})
        audio_data = await generate_audio(scene)

        if await job_service.is_job_cancelled(job_id):
            logger.info(
                "Audio processing completed but job cancelled",
                extra={"job_id": job_id, "scene_id": scene_id},
            )
            return

        segment_state = await composer.handle_asset_completion(
            job_id, scene_id, "audio", audio_data
        )
        await job_service.update_segment(job_id, scene_id, segment_state)

    except Exception as exc:
        logger.error(
            "Audio processing failed",
            extra={
                "job_id": job_id,
                "scene_id": scene_id,
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
            exc_info=True,
        )
        failure_data = {
            "path": "",
            "duration": 0,
            "status": "failed",
            "error": f"{type(exc).__name__}: {str(exc)}",
        }
        try:
            await composer.handle_asset_completion(job_id, scene_id, "audio", failure_data)
        except Exception as handler_error:
            logger.error(
                "Failed to record audio failure",
                extra={"job_id": job_id, "scene_id": scene_id, "error": str(handler_error)},
            )


async def _process_visual_asset(job_id: str, scene: dict) -> None:
    scene_id = scene["id"]

    if await job_service.is_job_cancelled(job_id):
        logger.info("Visual processing cancelled", extra={"job_id": job_id, "scene_id": scene_id})
        return

    try:
        logger.debug("Starting visual processing", extra={"job_id": job_id, "scene_id": scene_id})
        visual_data = await generate_visual_asset(scene, job_id)

        if await job_service.is_job_cancelled(job_id):
            logger.info(
                "Visual processing completed but job cancelled",
                extra={"job_id": job_id, "scene_id": scene_id},
            )
            return

        segment_state = await composer.handle_asset_completion(
            job_id, scene_id, "visual", visual_data
        )
        await job_service.update_segment(job_id, scene_id, segment_state)

    except Exception as exc:
        logger.error(
            "Visual processing failed",
            extra={
                "job_id": job_id,
                "scene_id": scene_id,
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
            exc_info=True,
        )
        failure_data = {
            "path": "",
            "status": "failed",
            "visual_type": scene.get("visual_type", "unknown"),
            "error": f"{type(exc).__name__}: {str(exc)}",
        }
        try:
            await composer.handle_asset_completion(job_id, scene_id, "visual", failure_data)
        except Exception as handler_error:
            logger.error(
                "Failed to record visual failure",
                extra={"job_id": job_id, "scene_id": scene_id, "error": str(handler_error)},
            )
