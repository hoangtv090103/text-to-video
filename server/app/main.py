import asyncio
import logging
import os
import time
import uuid
from collections.abc import Callable
from contextlib import asynccontextmanager
from enum import Enum
from typing import Any

import httpx
import uvicorn
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.error_handlers import register_exception_handlers
from app.core.logging_config import setup_logging
from app.orchestrator import create_video_job
from app.schemas.video import JobStatus, JobStatusResponse
from app.services.job_service import job_service
from app.services.llm_service import LLMService, check_llm_health
from app.utils.file import FileContext

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 50 * 1024 * 1024
ALLOWED_FILE_TYPES = {".txt", ".pdf", ".md"}
ALLOWED_CONTENT_TYPES = {"text/plain", "application/pdf", "text/markdown"}


class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = CircuitBreakerState.CLOSED

    def _can_attempt_call(self) -> bool:
        if self.state == CircuitBreakerState.CLOSED:
            return True
        if self.state == CircuitBreakerState.OPEN:
            if (
                self.last_failure_time
                and time.time() - self.last_failure_time >= self.recovery_timeout
            ):
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")
                return True
            return False
        return True

    def _record_success(self):
        self.failure_count = 0
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.CLOSED
            logger.info(f"Circuit breaker {self.name} transitioning to CLOSED")

    def _record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(
                f"Circuit breaker {self.name} transitioning to OPEN after {self.failure_count} failures"
            )

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        if not self._can_attempt_call():
            raise HTTPException(
                status_code=503, detail=f"Service {self.name} is temporarily unavailable"
            )
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as exc:
            self._record_failure()
            logger.error(f"Circuit breaker {self.name} recorded failure", extra={"error": str(exc)})
            raise


tts_circuit_breaker = CircuitBreaker("TTS", failure_threshold=5, recovery_timeout=60)
llm_circuit_breaker = CircuitBreaker("LLM", failure_threshold=5, recovery_timeout=60)


def validate_file_upload(file: UploadFile) -> None:
    """
    Validate file extension and content type.
    Note: Size validation should be done separately after reading file bytes.
    """
    file_extension = file.filename.lower() if file.filename else ""
    if not any(file_extension.endswith(ext) for ext in ALLOWED_FILE_TYPES):
        raise HTTPException(
            status_code=400, detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_FILE_TYPES)}"
        )

    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content type. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )

    logger.info(
        "File validation passed",
        extra={"uploaded_file": file.filename, "content_type": file.content_type},
    )


async def check_tts_health() -> bool:
    try:

        async def _health_check():
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{settings.TTS_SERVICE_URL.replace('/audio/speech', '')}/health"
                )
                if response.status_code == 200:
                    health_data = response.json()
                    return health_data.get("model_loaded", False)
                return False

        return await tts_circuit_breaker.call(_health_check)
    except Exception as exc:
        logger.error("TTS health check failed", extra={"error": str(exc)})
        return False


async def startup_health_checks() -> None:
    max_retries = 12
    base_delay = 5.0
    logger.info("Starting dependency health checks")

    for attempt in range(max_retries):
        logger.info(f"Checking TTS service health (attempt {attempt + 1}/{max_retries})")
        if await check_tts_health():
            logger.info("TTS service is healthy and model is loaded")
            break
        if attempt == max_retries - 1:
            logger.error("TTS service failed health check after maximum retries")
            raise RuntimeError("TTS service is not ready")
        logger.warning(f"TTS service not ready, retrying in {base_delay}s")
        await asyncio.sleep(base_delay)

    for attempt in range(max_retries):
        logger.info(f"Checking LLM service health (attempt {attempt + 1}/{max_retries})")
        if await check_llm_health():
            logger.info("LLM service is healthy")
            break
        if attempt == max_retries - 1:
            logger.error("LLM service failed health check after maximum retries")
            raise RuntimeError("LLM service is not ready")
        logger.warning(f"LLM service not ready, retrying in {base_delay}s")
        await asyncio.sleep(base_delay)

    logger.info("All dependency health checks passed")


def ensure_storage_directories():
    """Ensure persistent storage directories exist."""
    import os

    directories = [
        settings.ASSET_STORAGE_PATH,
        settings.VIDEO_OUTPUT_PATH,
        settings.VISUAL_STORAGE_PATH,
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Ensured storage directory exists: {directory}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Text-to-Video service starting up")
    # Ensure storage directories exist before starting
    ensure_storage_directories()
    await startup_health_checks()
    yield
    logger.info("Text-to-Video service shutting down")
    job_service.shutdown()


app = FastAPI(
    title="Text-to-Video Generation Service",
    description="Generate videos from text using parallel audio and visual processing",
    version="1.0.0",
    lifespan=lifespan,
)

# Register error handlers
register_exception_handlers(app)


# Request ID middleware for tracing
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add X-Request-ID header to all responses for request tracing."""
    import uuid

    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    # Bind request_id to structlog context
    from structlog import contextvars

    contextvars.bind_contextvars(request_id=request_id)

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    # Clear context after request
    contextvars.clear_contextvars()

    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm_service = LLMService()


@app.get(
    "/health",
    tags=["health"],
    summary="Health Check",
    description="Check service health and dependency status",
)
async def health_check():
    try:
        from datetime import UTC, datetime

        tts_healthy = await check_tts_health()
        llm_healthy = await check_llm_health()
        overall_status = "healthy" if (tts_healthy and llm_healthy) else "degraded"

        # Map health status to contract values: "up", "down", "circuit_open"
        # Check circuit breaker state first
        if tts_circuit_breaker.state == CircuitBreakerState.OPEN:
            tts_status = "circuit_open"
        else:
            tts_status = "up" if tts_healthy else "down"

        if llm_circuit_breaker.state == CircuitBreakerState.OPEN:
            llm_status = "circuit_open"
        else:
            llm_status = "up" if llm_healthy else "down"

        return {
            "status": overall_status,
            "service": "text-to-video",
            "dependencies": {"tts_service": tts_status, "llm_service": llm_status},
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as exc:
        logger.error("Health check failed", extra={"error": str(exc)})
        return {"status": "unhealthy", "service": "text-to-video", "error": str(exc)}


@app.post(
    "/api/v1/video/generate",
    response_model=JobStatusResponse,
    status_code=202,
    tags=["video"],
    summary="Generate Video",
    description="Upload a document (TXT/PDF/MD) to generate a narrated video. Returns a job ID for tracking progress.",
)
async def generate_video(
    background_tasks: BackgroundTasks, file: UploadFile = File(...)
) -> JobStatusResponse:
    try:
        job_id = str(uuid.uuid4())

        # Read file contents first to get actual size
        contents = await file.read()
        file_size = len(contents)

        # Validate size using actual bytes read
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size {MAX_FILE_SIZE // (1024 * 1024)}MB",
            )

        # Reset file pointer for validation
        await file.seek(0)
        validate_file_upload(file)

        logger.info(
            "Video generation request received",
            extra={"job_id": job_id, "uploaded_file": file.filename, "size_bytes": file_size},
        )
        file_context = FileContext(contents=contents, filename=file.filename)

        await job_service.initialize_job(job_id, message="Job queued for processing", progress=5)
        await job_service.add_to_queue(job_id)

        background_tasks.add_task(create_video_job, job_id=job_id, file=file_context)

        from datetime import UTC, datetime

        now = datetime.now(UTC).isoformat()

        response = JobStatusResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message=None,
            progress=None,
            created_at=now,
            updated_at=now,
            completed_at=None,
            result=None,
        )
        logger.info("Video generation job queued", extra={"job_id": job_id, "status": "pending"})
        return response

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to create video generation job",
            extra={"error": str(exc), "uploaded_file": file.filename},
        )
        raise HTTPException(
            status_code=500, detail="Internal server error while creating video generation job"
        )


@app.get(
    "/api/v1/video/status/{job_id}",
    response_model=JobStatusResponse,
    tags=["video"],
    summary="Get Job Status",
    description="Check the status of a video generation job by its ID",
)
async def get_job_status(job_id: str):
    try:
        # Validate UUID format
        import uuid as uuid_lib

        try:
            uuid_lib.UUID(job_id)
        except ValueError:
            raise HTTPException(
                status_code=422, detail="Invalid job ID format. Must be a valid UUID."
            )

        logger.info("Job status requested", extra={"job_id": job_id})
        job_data = await job_service.get_job_status(job_id)
        if not job_data:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        result_data = None
        if job_data.get("status") in ["completed", "completed_with_errors", "failed"]:
            raw_result = await job_service.get_job_result(job_id)
            if raw_result:
                # Transform result data to match JobResult schema
                result_data = {}

                # Handle video info
                if "video" in raw_result:
                    video_info = raw_result["video"]
                    # Add video URL if video exists
                    if video_info.get("video_path") and os.path.exists(video_info["video_path"]):
                        video_info["video_url"] = f"/api/v1/video/download/{job_id}"
                    result_data["video"] = video_info

                # Handle script - convert list to count if needed
                if "script" in raw_result:
                    script = raw_result["script"]
                    if isinstance(script, dict) and "scenes" in script:
                        result_data["script_scenes"] = len(script.get("scenes", []))
                        result_data["script"] = script
                    elif isinstance(script, list):  # If it's already a list of scenes
                        result_data["script_scenes"] = len(script)

                # Copy other fields
                result_data["successful_tasks"] = raw_result.get("successful_tasks", 0)
                result_data["failed_tasks"] = raw_result.get("failed_tasks", 0)
                result_data["processing_time_seconds"] = raw_result.get("processing_time_seconds")
                result_data["errors"] = raw_result.get("errors", [])

        from datetime import UTC, datetime

        now = datetime.now(UTC).isoformat()

        return JobStatusResponse(
            job_id=job_data.get("job_id", job_id),
            status=job_data.get("status", "unknown"),
            phase=job_data.get("phase"),
            message=job_data.get("message"),
            progress=job_data.get("progress"),
            created_at=job_data.get("created_at", now),
            updated_at=job_data.get("updated_at", now),
            completed_at=job_data.get("completed_at"),
            result=result_data,  # type: ignore
            errors=job_data.get("errors"),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get job status", extra={"job_id": job_id, "error": str(exc)})
        raise HTTPException(status_code=500, detail="Failed to retrieve job status")


@app.get(
    "/api/v1/video/jobs",
    tags=["video"],
    summary="List Jobs",
    description="Get a list of all video generation jobs",
)
async def list_jobs(limit: int = 10):
    try:
        limit = min(limit, 100)
        job_ids = await job_service.list_jobs(limit=limit)
        jobs = []
        for job_id in job_ids:
            job_data = await job_service.get_job_status(job_id)
            if job_data:
                jobs.append(
                    {
                        "job_id": job_id,
                        "status": job_data.get("status", "unknown"),
                        "message": job_data.get("message"),
                        "progress": job_data.get("progress"),
                        "updated_at": job_data.get("updated_at"),
                    }
                )
        return {"jobs": jobs, "total_count": len(jobs)}
    except Exception as exc:
        logger.error("Failed to list jobs", extra={"error": str(exc)})
        raise HTTPException(status_code=500, detail="Failed to list jobs")


@app.post(
    "/api/v1/video/cancel/{job_id}",
    tags=["video"],
    summary="Cancel Job",
    description="Cancel a running video generation job",
)
async def cancel_job(job_id: str, reason: str = "User requested cancellation"):
    try:
        logger.info("Job cancellation requested", extra={"job_id": job_id, "reason": reason})
        try:
            uuid.UUID(job_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid job ID format")

        success = await job_service.cancel_job(job_id, reason)
        if success:
            logger.info("Job cancelled successfully", extra={"job_id": job_id})
            return {"message": "Job cancelled successfully", "job_id": job_id, "reason": reason}

        job_data = await job_service.get_job_status(job_id)
        if job_data:
            current_status = job_data.get("status", "unknown")
            raise HTTPException(
                status_code=409, detail=f"Cannot cancel job in status: {current_status}"
            )
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to cancel job", extra={"job_id": job_id, "error": str(exc)})
        raise HTTPException(
            status_code=500, detail=f"Internal server error while cancelling job: {str(exc)}"
        )


@app.get("/api/v1/video/active")
async def get_active_jobs(limit: int = 50):
    try:
        limit = min(limit, 100)
        active_jobs = await job_service.get_active_jobs(limit=limit)
        return {"active_jobs": active_jobs, "total_count": len(active_jobs), "limit": limit}
    except Exception as exc:
        logger.error("Failed to get active jobs", extra={"error": str(exc)})
        raise HTTPException(status_code=500, detail="Failed to retrieve active jobs")


@app.post(
    "/api/v1/admin/cleanup",
    tags=["admin"],
    summary="Cleanup Resources",
    description="Manually trigger cleanup of old jobs and temporary files",
)
async def cleanup_resources():
    try:
        logger.info("Resource cleanup requested")
        cleanup_result = job_service.run_cleanup(max_age_hours=24)
        return {
            "message": "Cleanup completed successfully",
            "job_cleanup": cleanup_result,
            "timestamp": time.time(),
        }
    except Exception as exc:
        logger.error("Resource cleanup failed", extra={"error": str(exc)})
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(exc)}")


@app.get(
    "/api/v1/video/download/{job_id}",
    tags=["video"],
    summary="Download Video",
    description="Download or stream the generated video file for a completed job",
)
async def download_video(job_id: str, download: bool = False):
    """
    Download or stream video file for a completed job.

    Args:
        job_id: Job identifier
        download: If True, force download; if False, stream for viewing
    """
    try:
        logger.info("Video download requested", extra={"job_id": job_id, "download": download})

        # Get job data
        job_data = await job_service.get_job_status(job_id)
        if not job_data:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Check if job is failed - no video available
        if job_data.get("status") == "failed":
            raise HTTPException(
                status_code=404, detail=f"No video available for failed job {job_id}"
            )

        # Check if job is completed
        if job_data.get("status") not in ["completed", "completed_with_errors"]:
            raise HTTPException(status_code=400, detail=f"Job {job_id} is not ready yet")

        # Get result data
        result_data = await job_service.get_job_result(job_id)
        if not result_data or not result_data.get("video", {}).get("video_path"):
            raise HTTPException(status_code=404, detail=f"No video found for job {job_id}")

        video_path = result_data["video"]["video_path"]
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail=f"Video file not found: {video_path}")

        # Get file info
        file_size = os.path.getsize(video_path)
        filename = f"video_{job_id}.mp4"

        logger.info(
            "Serving video file",
            extra={
                "job_id": job_id,
                "video_path": video_path,
                "file_size": file_size,
                "download": download,
            },
        )

        # Set appropriate headers
        headers = {"Content-Length": str(file_size), "Accept-Ranges": "bytes"}

        if download:
            headers["Content-Disposition"] = f"attachment; filename={filename}"
        else:
            headers["Content-Disposition"] = f"inline; filename={filename}"

        return FileResponse(
            path=video_path, media_type="video/mp4", filename=filename, headers=headers
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to serve video", extra={"job_id": job_id, "error": str(exc)})
        raise HTTPException(status_code=500, detail=f"Failed to serve video: {str(exc)}")


@app.get("/api/v1/video/stream/{job_id}")
async def stream_video(job_id: str):
    """
    Stream video for viewing in browser.
    """
    return await download_video(job_id, download=False)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
