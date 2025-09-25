import uuid
import logging
import asyncio
import httpx
import uvicorn
from datetime import datetime, timezone
from fastapi import FastAPI, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.logging_config import setup_logging
from app.core.config import settings
from app.schemas.video import JobStatusResponse, validate_file_upload, validate_job_id, MAX_FILE_SIZE
from app.orchestrator import create_video_job
from app.services.llm_service import LLMService, check_llm_health
from app.utils.file import FileContext

logger = logging.getLogger(__name__)

# Standardized error responses
ERROR_CODES = {
    "SERVICE_UNAVAILABLE": {"code": 503, "message": "Service temporarily unavailable"},
    "VALIDATION_ERROR": {"code": 400, "message": "Invalid input data"},
    "NOT_FOUND": {"code": 404, "message": "Resource not found"},
    "INTERNAL_ERROR": {"code": 500, "message": "Internal server error"},
    "REDIS_UNAVAILABLE": {"code": 503, "message": "Job tracking service unavailable"}
}

def handle_service_error(error: Exception, operation: str, **context) -> HTTPException:
    """Standardized error handling with specific error types and clear messages."""
    error_type = type(error).__name__
    
    # Map specific exceptions to error codes
    if "ConnectionError" in error_type or "TimeoutError" in error_type:
        error_info = ERROR_CODES["SERVICE_UNAVAILABLE"]
        detail = f"{operation} failed: External service unavailable"
    elif "ValidationError" in error_type or error_type == "HTTPException":
        raise error  # Re-raise validation errors as-is
    else:
        error_info = ERROR_CODES["INTERNAL_ERROR"]
        detail = f"{operation} failed: {error_info['message']}"
    
    logger.error(f"{operation} failed", extra={
        "error_type": error_type,
        "error": str(error),
        **context
    })
    
    return HTTPException(status_code=error_info["code"], detail=detail)

# Track application start time for uptime calculation
APP_START_TIME = datetime.now(timezone.utc)

# Import redis_service at module level but handle potential import errors gracefully
try:
    from app.services.redis_service import redis_service, check_redis_health
    REDIS_AVAILABLE = True
except ImportError as e:
    print(f"Redis service not available: {e}")
    redis_service = None
    check_redis_health = None
    REDIS_AVAILABLE = False


async def check_tts_health() -> bool:
    """
    Check if the TTS service is healthy and model is loaded.

    Returns:
        True if TTS service is ready, False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{settings.TTS_SERVICE_URL.replace('/audio/speech', '')}/health")

            if response.status_code == 200:
                health_data = response.json()
                model_loaded = health_data.get("model_loaded", False)
                return model_loaded

            return False

    except Exception as e:
        logger.error("TTS health check failed", extra={"error": str(e)})
        return False


async def startup_health_checks():
    """
    Perform startup health checks for critical dependencies.
    Application will not start accepting requests until all checks pass.
    """
    max_retries = 12  # 12 attempts with 5s intervals = 1 minute max wait
    base_delay = 5.0

    logger.info("Starting dependency health checks")

    # Check TTS service
    for attempt in range(max_retries):
        logger.info(f"Checking TTS service health (attempt {attempt + 1}/{max_retries})")

        if await check_tts_health():
            logger.info("TTS service is healthy and model is loaded")
            break

        if attempt == max_retries - 1:
            logger.error("TTS service failed health check after maximum retries")
            raise RuntimeError("TTS service is not ready - application cannot start")

        logger.warning(f"TTS service not ready, retrying in {base_delay}s")
        await asyncio.sleep(base_delay)

    # Check LLM service
    for attempt in range(max_retries):
        logger.info(f"Checking LLM service health (attempt {attempt + 1}/{max_retries})")

        if await check_llm_health():
            logger.info("LLM service is healthy")
            break

        if attempt == max_retries - 1:
            logger.error("LLM service failed health check after maximum retries")
            raise RuntimeError("LLM service is not ready - application cannot start")

        logger.warning(f"LLM service not ready, retrying in {base_delay}s")
        await asyncio.sleep(base_delay)

    logger.info("All dependency health checks passed - application ready to accept requests")


def ensure_storage_directories():
    """Ensure persistent storage directories exist."""
    import os
    directories = [
        settings.ASSET_STORAGE_PATH,
        settings.VIDEO_OUTPUT_PATH,
        settings.VISUAL_STORAGE_PATH
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Ensured storage directory exists: {directory}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    setup_logging()
    logger.info("Text-to-Video service starting up")
    
    # Ensure persistent storage directories exist
    ensure_storage_directories()

    # Perform health checks before accepting requests
    await startup_health_checks()

    yield

    # Shutdown
    logger.info("Text-to-Video service shutting down")

    # Close Redis connection if available
    if REDIS_AVAILABLE and redis_service:
        try:
            await redis_service.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error("Error closing Redis connection", extra={"error": str(e)})


# Create FastAPI app with lifespan management
app = FastAPI(
    title="Text-to-Video Generation Service",
    description="A scalable microservice for generating videos from text using parallel audio and visual processing",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm_service = LLMService(

)

@app.get("/health")
async def health_check():
    """
    Health check endpoint with dependency status.
    """
    try:
        # Check dependencies
        tts_healthy = await check_tts_health()
        llm_healthy = await check_llm_health()
        redis_healthy = await check_redis_health() if REDIS_AVAILABLE and check_redis_health else False

        overall_status = "healthy" if (tts_healthy and llm_healthy and redis_healthy) else "degraded"
        
        # Calculate uptime
        current_time = datetime.now(timezone.utc)
        uptime_seconds = (current_time - APP_START_TIME).total_seconds()

        return {
            "status": overall_status,
            "service": "text-to-video",
            "dependencies": {
                "tts_service": "healthy" if tts_healthy else "unhealthy",
                "llm_service": "healthy" if llm_healthy else "unhealthy",
                "redis_service": "healthy" if redis_healthy else "unhealthy"
            },
            "timestamp": current_time.isoformat(),
            "uptime_seconds": uptime_seconds,
            "started_at": APP_START_TIME.isoformat()
        }

    except Exception as e:
        logger.error("Health check failed", extra={"error_type": type(e).__name__, "error": str(e)})
        return {
            "status": "unhealthy",
            "service": "text-to-video",
            "error": "Health check service failure"
        }


@app.post("/api/v1/video/generate", response_model=JobStatusResponse)
async def generate_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
) -> JobStatusResponse:
    """
    Generate a video from source text.

    This endpoint accepts source text and orchestrates the generation of audio and visual assets
    in parallel, composing them into a final video. The processing happens asynchronously
    in the background.

    Args:
        request: Video generation request with source text
        background_tasks: FastAPI background tasks for asynchronous processing

    Returns:
        Job status response with unique job ID and status

    Raises:
        HTTPException: If request validation fails or service is unavailable
    """
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # Validate file upload
        if not file:
            raise HTTPException(status_code=400, detail="File cannot be empty")
        
        validate_file_upload(file)
        
        # Check file size
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
            )


        # Log request
        logger.info("Video generation request received", extra={
            "job_id": job_id,
            "file": file.filename
        })

        file_context = FileContext(contents=contents, filename=file.filename)

        # Set initial job status in Redis if available
        if REDIS_AVAILABLE and redis_service:
            await redis_service.set_job_status(
                job_id=job_id,
                status="pending",
                message="Job queued for processing"
            )

        # Add video job creation to background tasks
        background_tasks.add_task(
            create_video_job,
            job_id=job_id,
            file=file_context
        )

        # Return immediate response with job ID
        response = JobStatusResponse(
            job_id=job_id,
            status="pending"
        )

        logger.info("Video generation job queued", extra={
            "job_id": job_id,
            "status": "pending"
        })

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise handle_service_error(e, "Video generation job creation", file=file.filename)


@app.get("/api/v1/video/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a video generation job.

    Args:
        job_id: Unique identifier for the video generation job

    Returns:
        Current job status and progress information with detailed metadata
    """
    try:
        # Validate job ID format
        validate_job_id(job_id)
        
        logger.info("Job status requested", extra={"job_id": job_id})

        # Check if Redis is available
        if not REDIS_AVAILABLE or not redis_service:
            error_info = ERROR_CODES["REDIS_UNAVAILABLE"]
            raise HTTPException(
                status_code=error_info["code"],
                detail=error_info["message"]
            )

        # Query Redis for job status
        job_data = await redis_service.get_job_status(job_id)

        if not job_data:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )

        # Get job result if completed
        result_data = None
        if job_data.get("status") in ["completed", "completed_with_errors"]:
            result_data = await redis_service.get_job_result(job_id)

        # Build response
        response = JobStatusResponse(
            job_id=job_data.get("job_id", job_id),
            status=job_data.get("status", "unknown"),
            message=job_data.get("message"),
            progress=job_data.get("progress"),
            updated_at=job_data.get("updated_at"),
            completed_at=job_data.get("completed_at"),
            result=result_data
        )

        logger.info("Job status retrieved", extra={
            "job_id": job_id,
            "status": response.status,
            "progress": response.progress
        })

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise handle_service_error(e, "Job status retrieval", job_id=job_id)


@app.get("/api/v1/video/jobs")
async def list_jobs(limit: int = 10):
    """
    List recent video generation jobs.

    Args:
        limit: Maximum number of jobs to return (default: 10, max: 100)

    Returns:
        List of job IDs and their basic status
    """
    try:
        # Limit the number of results to prevent overwhelming the response
        limit = min(limit, 100)

        # Check if Redis is available
        if not REDIS_AVAILABLE or not redis_service:
            raise HTTPException(
                status_code=503,
                detail="Job listing service is not available"
            )

        # Get list of job IDs
        job_ids = await redis_service.list_jobs(limit=limit)

        # Get basic status for each job
        jobs = []
        for job_id in job_ids:
            job_data = await redis_service.get_job_status(job_id)
            if job_data:
                jobs.append({
                    "job_id": job_id,
                    "status": job_data.get("status", "unknown"),
                    "message": job_data.get("message"),
                    "progress": job_data.get("progress"),
                    "updated_at": job_data.get("updated_at")
                })

        return {
            "jobs": jobs,
            "total_count": len(jobs)
        }

    except Exception as e:
        logger.error("Failed to list jobs", extra={"error": str(e)})
        raise HTTPException(
            status_code=500,
            detail="Failed to list jobs"
        )


@app.post("/api/v1/video/generate-sync")
async def generate_video_sync(
    file: UploadFile = File(...)
):
    """
    Generate a video from source text synchronously.

    This endpoint processes the request synchronously without using Redis or background tasks.
    The processing happens directly in the request handler and returns the complete result.

    Args:
        file: Uploaded file containing source content

    Returns:
        Complete video generation result with all assets and processing details

    Raises:
        HTTPException: If request validation fails or processing errors occur
    """
    try:
        # Generate unique job ID for tracking
        job_id = str(uuid.uuid4())

        # Validate file upload
        if not file:
            raise HTTPException(status_code=400, detail="File cannot be empty")
        
        validate_file_upload(file)
        
        # Check file size
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
            )

        # Log request
        logger.info("Synchronous video generation request received", extra={
            "job_id": job_id,
            "file": file.filename
        })

        # Create file context with already-read contents
        file_context = FileContext(contents=contents, filename=file.filename)

        # Import and run synchronous orchestrator
        from app.orchestrator_sync import create_video_job_sync

        # Process synchronously - this will block until completion
        result = create_video_job_sync(job_id=job_id, file=file_context)

        # Log completion
        logger.info("Synchronous video generation completed", extra={
            "job_id": job_id,
            "status": result.get("status"),
            "processing_time": result.get("processing_time")
        })

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise handle_service_error(e, "Synchronous video generation", file=file.filename if file else "No file")


@app.get("/api/v1/video/download/{job_id}")
async def download_video(job_id: str):
    """
    Download the generated video file for a completed job.

    Args:
        job_id: The job ID for the video to download

    Returns:
        FileResponse: The video file for download

    Raises:
        HTTPException: If video file not found or job not completed
    """
    try:
        from fastapi.responses import FileResponse
        import os

        # Check if video file exists
        video_path = f"{settings.VIDEO_OUTPUT_PATH}/job_{job_id}_final_video.mp4"

        if not os.path.exists(video_path):
            raise HTTPException(
                status_code=404,
                detail="Video file not found. Job may not be completed or file may have been cleaned up."
            )

        logger.info("Video download requested", extra={
            "job_id": job_id,
            "video_path": video_path
        })

        return FileResponse(
            path=video_path,
            media_type="video/mp4",
            filename=f"video_{job_id}.mp4"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to download video", extra={
            "job_id": job_id,
            "error": str(e)
        })
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error while downloading video: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
