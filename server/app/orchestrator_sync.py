import logging
from typing import Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from app.utils.file import FileContext

logger = logging.getLogger(__name__)


def create_video_job_sync(job_id: str, file: FileContext) -> Dict:
    """
    Core business logic for creating a video job synchronously.
    Orchestrates the generation of audio and visual assets in parallel using threading.

    Args:
        job_id: Unique identifier for the video generation job
        file: File context containing the source content

    Returns:
        Dict containing job result and status
    """
    logger.info("Starting synchronous video job creation", extra={
        "job_id": job_id,
        "file_name": file.filename
    })

    start_time = time.time()

    try:
        # Step 1: Generate script from source text using LLM service
        logger.info("Generating script from source text")
        from app.services.llm_service_sync import generate_script_sync
        script_scenes = generate_script_sync(file)

        logger.info("Script generated successfully", extra={
            "job_id": job_id,
            "total_scenes": len(script_scenes)
        })

        # Step 2: Process each scene with parallel audio and visual generation
        logger.info("Starting parallel asset generation using ThreadPoolExecutor")

        all_assets = []

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all tasks
            future_to_task = {}

            for scene in script_scenes:
                scene_id = scene["id"]

                # Submit audio generation task
                audio_future = executor.submit(
                    _process_audio_asset_sync,
                    job_id,
                    scene
                )
                future_to_task[audio_future] = ("audio", scene_id)

                # Submit visual generation task
                visual_future = executor.submit(
                    _process_visual_asset_sync,
                    job_id,
                    scene
                )
                future_to_task[visual_future] = ("visual", scene_id)

            # Collect results as they complete
            successful_tasks = 0
            failed_tasks = 0

            for future in as_completed(future_to_task):
                asset_type, scene_id = future_to_task[future]

                try:
                    result = future.result()
                    if result and result.get("status") != "failed":
                        successful_tasks += 1
                        all_assets.append({
                            "scene_id": scene_id,
                            "asset_type": asset_type,
                            "data": result
                        })
                        logger.info(f"{asset_type.capitalize()} asset completed", extra={
                            "job_id": job_id,
                            "scene_id": scene_id
                        })
                    else:
                        failed_tasks += 1
                        logger.error(f"{asset_type.capitalize()} asset failed", extra={
                            "job_id": job_id,
                            "scene_id": scene_id,
                            "error": result.get("error", "Unknown error") if result else "No result"
                        })

                except Exception as e:
                    failed_tasks += 1
                    logger.error(f"{asset_type.capitalize()} task failed with exception", extra={
                        "job_id": job_id,
                        "scene_id": scene_id,
                        "error": str(e)
                    })

        # Step 3: Prepare final result
        end_time = time.time()
        total_time = end_time - start_time

        # Group assets by scene
        scenes_with_assets = {}
        for asset in all_assets:
            scene_id = asset["scene_id"]
            if scene_id not in scenes_with_assets:
                scenes_with_assets[scene_id] = {
                    "scene_id": scene_id,
                    "audio": None,
                    "visual": None
                }
            scenes_with_assets[scene_id][asset["asset_type"]] = asset["data"]

        # Log completion statistics
        total_tasks = successful_tasks + failed_tasks
        logger.info("Video job processing completed", extra={
            "job_id": job_id,
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
            "processing_time": f"{total_time:.2f}s"
        })

        # Step 3: Video Composition - Combine audio and visual assets into final video
        logger.info("Starting video composition (Phase 3)")

        try:
            from app.services.video_composer_sync import compose_video_sync

            # Only proceed with composition if we have valid scenes
            if scenes_with_assets:
                composition_result = compose_video_sync(
                    scenes_with_assets=list(scenes_with_assets.values()),
                    job_id=job_id
                )

                # Update final result with video composition info
                if composition_result.get("status") == "success":
                    logger.info("Video composition completed successfully", extra={
                        "job_id": job_id,
                        "video_path": composition_result.get("video_path"),
                        "video_duration": composition_result.get("duration"),
                        "file_size_mb": composition_result.get("file_size_mb")
                    })

                    final_result = {
                        "job_id": job_id,
                        "status": "completed",
                        "message": "Video generation completed successfully with final video",
                        "total_scenes": len(script_scenes),
                        "successful_tasks": successful_tasks,
                        "failed_tasks": failed_tasks,
                        "processing_time": total_time,
                        "scenes": list(scenes_with_assets.values()),
                        "script_scenes": script_scenes,
                        "video": composition_result  # Include video composition result
                    }
                else:
                    logger.error("Video composition failed", extra={
                        "job_id": job_id,
                        "error": composition_result.get("error")
                    })

                    final_result = {
                        "job_id": job_id,
                        "status": "completed_with_composition_error",
                        "message": f"Assets generated but video composition failed: {composition_result.get('error')}",
                        "total_scenes": len(script_scenes),
                        "successful_tasks": successful_tasks,
                        "failed_tasks": failed_tasks,
                        "processing_time": total_time,
                        "scenes": list(scenes_with_assets.values()),
                        "script_scenes": script_scenes,
                        "composition_error": composition_result.get("error")
                    }
            else:
                logger.warning("No valid scenes for video composition", extra={"job_id": job_id})
                final_result = {
                    "job_id": job_id,
                    "status": "failed",
                    "message": "No valid scenes with both audio and visual assets for video composition",
                    "total_scenes": len(script_scenes),
                    "successful_tasks": successful_tasks,
                    "failed_tasks": failed_tasks,
                    "processing_time": total_time,
                    "scenes": list(scenes_with_assets.values()),
                    "script_scenes": script_scenes
                }

        except ImportError:
            logger.error("Video composition module not available", extra={
                "job_id": job_id,
                "error": "MoviePy not installed"
            })

            # Fallback: return results without video composition
            final_result = {
                "job_id": job_id,
                "status": "completed_without_video",
                "message": "Assets generated but video composition unavailable: MoviePy not installed",
                "total_scenes": len(script_scenes),
                "successful_tasks": successful_tasks,
                "failed_tasks": failed_tasks,
                "processing_time": total_time,
                "scenes": list(scenes_with_assets.values()),
                "script_scenes": script_scenes,
                "composition_error": "MoviePy not installed"
            }
        except Exception as composition_error:
            logger.error("Video composition module error", extra={
                "job_id": job_id,
                "error": str(composition_error)
            })

            # Fallback: return results without video composition
            final_result = {
                "job_id": job_id,
                "status": "completed_without_video",
                "message": f"Assets generated but video composition unavailable: {str(composition_error)}",
                "total_scenes": len(script_scenes),
                "successful_tasks": successful_tasks,
                "failed_tasks": failed_tasks,
                "processing_time": total_time,
                "scenes": list(scenes_with_assets.values()),
                "script_scenes": script_scenes,
                "composition_error": str(composition_error)
            }

        return final_result

    except Exception as e:
        end_time = time.time()
        total_time = end_time - start_time

        logger.error("Video job creation failed", extra={
            "job_id": job_id,
            "error": str(e),
            "processing_time": f"{total_time:.2f}s"
        })

        return {
            "job_id": job_id,
            "status": "failed",
            "message": f"Job failed: {str(e)}",
            "processing_time": total_time,
            "error": str(e)
        }


def _process_audio_asset_sync(job_id: str, scene: Dict) -> Dict:
    """
    Process audio asset generation for a scene synchronously.

    Args:
        job_id: Unique identifier for the video generation job
        scene: Scene data dictionary

    Returns:
        Audio asset data dictionary
    """
    scene_id = scene["id"]

    try:
        logger.debug("Starting audio processing", extra={
            "job_id": job_id,
            "scene_id": scene_id
        })

        # Generate audio asset using synchronous service
        from app.services.tts_service_sync import generate_audio_sync
        audio_data = generate_audio_sync(scene)

        logger.debug("Audio processing completed", extra={
            "job_id": job_id,
            "scene_id": scene_id
        })

        return audio_data

    except Exception as e:
        logger.error("Audio processing failed", extra={
            "job_id": job_id,
            "scene_id": scene_id,
            "error": str(e)
        })

        return {
            "path": "",
            "duration": 0,
            "status": "failed",
            "error": str(e)
        }


def _process_visual_asset_sync(job_id: str, scene: Dict) -> Dict:
    """
    Process visual asset generation for a scene synchronously.

    Args:
        job_id: Unique identifier for the video generation job
        scene: Scene data dictionary

    Returns:
        Visual asset data dictionary
    """
    scene_id = scene["id"]

    try:
        logger.debug("Starting visual processing", extra={
            "job_id": job_id,
            "scene_id": scene_id
        })

        # Generate visual asset using synchronous service
        from app.services.visual_services_sync import generate_visual_asset_sync
        visual_data = generate_visual_asset_sync(scene, job_id)

        logger.debug("Visual processing completed", extra={
            "job_id": job_id,
            "scene_id": scene_id
        })

        return visual_data

    except Exception as e:
        logger.error("Visual processing failed", extra={
            "job_id": job_id,
            "scene_id": scene_id,
            "error": str(e)
        })

        return {
            "path": "",
            "status": "failed",
            "visual_type": scene.get("visual_type", "unknown"),
            "error": str(e)
        }
