import uuid
import logging
import asyncio
import httpx
import uvicorn
import time
from enum import Enum
from typing import Dict, Optional, Callable, Any
from fastapi import FastAPI, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from app.core.logging_config import setup_logging
from app.core.config import settings
from app.schemas.video import JobStatus, JobStatusResponse
from app.orchestrator import create_video_job
from app.services.llm_service import LLMService, check_llm_health
from app.services.job_service import job_service
from app.utils.file import FileContext

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 50 * 1024 * 1024
ALLOWED_FILE_TYPES = {'.txt', '.pdf', '.md'}
ALLOWED_CONTENT_TYPES = {'text/plain', 'application/pdf', 'text/markdown'}


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
        self.last_failure_time: Optional[float] = None
        self.state = CircuitBreakerState.CLOSED

    def _can_attempt_call(self) -> bool:
        if self.state == CircuitBreakerState.CLOSED:
            return True
        if self.state == CircuitBreakerState.OPEN:
            if self.last_failure_time and time.time() - self.last_failure_time >= self.recovery_timeout:
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
            logger.warning(f"Circuit breaker {self.name} transitioning to OPEN after {self.failure_count} failures")

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        if not self._can_attempt_call():
            raise HTTPException(status_code=503, detail=f"Service {self.name} is temporarily unavailable")
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as exc:
            self._record_failure()
            logger.error(f"Circuit breaker {self.name} recorded failure", extra={"error": str(exc)})
            raise


tts_circuit_breaker = CircuitBreaker("TTS", failure_threshold=3, recovery_timeout=30)
llm_circuit_breaker = CircuitBreaker("LLM", failure_threshold=3, recovery_timeout=30)


def validate_file_upload(file: UploadFile) -> None:
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size {MAX_FILE_SIZE // (1024*1024)}MB")

    file_extension = file.filename.lower() if file.filename else ""
    if not any(file_extension.endswith(ext) for ext in ALLOWED_FILE_TYPES):
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_FILE_TYPES)}")

    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid content type. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}")

    logger.info("File validation passed", extra={
        "file_name": file.filename,
        "size": file.size,
        "content_type": file.content_type
    })


async def check_tts_health() -> bool:
    try:
        async def _health_check():
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{settings.TTS_SERVICE_URL.replace('/audio/speech', '')}/health")
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
        settings.VISUAL_STORAGE_PATH
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Ensured storage directory exists: {directory}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Text-to-Video service starting up")
    await startup_health_checks()
    yield
    logger.info("Text-to-Video service shutting down")
    job_service.shutdown()


app = FastAPI(
    title="Text-to-Video Generation Service",
    description="Generate videos from text using parallel audio and visual processing",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm_service = LLMService()


@app.get("/health")
async def health_check():
    try:
        tts_healthy = await check_tts_health()
        llm_healthy = await check_llm_health()
        overall_status = "healthy" if (tts_healthy and llm_healthy) else "degraded"
        return {
            "status": overall_status,
            "service": "text-to-video",
            "dependencies": {
                "tts_service": "healthy" if tts_healthy else "unhealthy",
                "llm_service": "healthy" if llm_healthy else "unhealthy",
                "redis_service": "healthy" if redis_healthy else "unhealthy"
            },
            "timestamp": time.time()
        }
    except Exception as exc:
        logger.error("Health check failed", extra={"error": str(exc)})
        return {
            "status": "unhealthy",
            "service": "text-to-video",
            "error": str(exc)
        }


@app.post("/api/v1/video/generate", response_model=JobStatusResponse)
async def generate_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)) -> JobStatusResponse:
    try:
        job_id = str(uuid.uuid4())
        validate_file_upload(file)

        logger.info("Video generation request received", extra={"job_id": job_id, "file_name": file.filename})
        contents = await file.read()
        file_context = FileContext(contents=contents, filename=file.filename)

        await job_service.initialize_job(job_id, message="Job queued for processing", progress=5)
        await job_service.add_to_queue(job_id)

        background_tasks.add_task(create_video_job, job_id=job_id, file=file_context)

        response = JobStatusResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message=None,
            progress=None,
            updated_at=None,
            completed_at=None,
            result=None
        )
        logger.info("Video generation job queued", extra={"job_id": job_id, "status": "pending"})
        return response

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to create video generation job", extra={"error": str(exc), "file_name": file.filename})
        raise HTTPException(status_code=500, detail="Internal server error while creating video generation job")


@app.get("/api/v1/video/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    try:
        # Validate job ID format
        validate_job_id(job_id)
        
        logger.info("Job status requested", extra={"job_id": job_id})
        job_data = await job_service.get_job_status(job_id)
        if not job_data:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        result_data = None
        if job_data.get("status") in ["completed", "completed_with_errors"]:
            result_data = await job_service.get_job_result(job_id)

        return JobStatusResponse(
            job_id=job_data.get("job_id", job_id),
            status=job_data.get("status", "unknown"),
            message=job_data.get("message"),
            progress=job_data.get("progress"),
            updated_at=job_data.get("updated_at"),
            completed_at=job_data.get("completed_at"),
            result=result_data
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get job status", extra={"job_id": job_id, "error": str(exc)})
        raise HTTPException(status_code=500, detail="Failed to retrieve job status")


@app.get("/api/v1/video/jobs")
async def list_jobs(limit: int = 10):
    try:
        limit = min(limit, 100)
        job_ids = await job_service.list_jobs(limit=limit)
        jobs = []
        for job_id in job_ids:
            job_data = await job_service.get_job_status(job_id)
            if job_data:
                jobs.append({
                    "job_id": job_id,
                    "status": job_data.get("status", "unknown"),
                    "message": job_data.get("message"),
                    "progress": job_data.get("progress"),
                    "updated_at": job_data.get("updated_at")
                })
        return {"jobs": jobs, "total_count": len(jobs)}
    except Exception as exc:
        logger.error("Failed to list jobs", extra={"error": str(exc)})
        raise HTTPException(status_code=500, detail="Failed to list jobs")


@app.post("/api/v1/video/cancel/{job_id}")
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
            raise HTTPException(status_code=409, detail=f"Cannot cancel job in status: {current_status}")
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to cancel job", extra={"job_id": job_id, "error": str(exc)})
        raise HTTPException(status_code=500, detail=f"Internal server error while cancelling job: {str(exc)}")


@app.get("/api/v1/video/active")
async def get_active_jobs(limit: int = 50):
    try:
        limit = min(limit, 100)
        active_jobs = await job_service.get_active_jobs(limit=limit)
        return {"active_jobs": active_jobs, "total_count": len(active_jobs), "limit": limit}
    except Exception as exc:
        logger.error("Failed to get active jobs", extra={"error": str(exc)})
        raise HTTPException(status_code=500, detail="Failed to retrieve active jobs")


@app.post("/api/v1/admin/cleanup")
async def cleanup_resources():
    try:
        logger.info("Resource cleanup requested")
        cleanup_result = job_service.run_cleanup(max_age_hours=24)
        return {
            "message": "Cleanup completed successfully",
            "job_cleanup": cleanup_result,
            "timestamp": time.time()
        }
    except Exception as exc:
        logger.error("Resource cleanup failed", extra={"error": str(exc)})
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(exc)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
