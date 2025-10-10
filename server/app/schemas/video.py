"""
Pydantic schemas for the Text-to-Video service.

This module defines all data models used throughout the application,
following the specifications in specs/001-build-a-service/data-model.md

Entities:
- Job: Video generation request lifecycle
- Script: LLM-generated scene breakdown (3-7 scenes)
- Scene: Single video segment (narration + visual)
- AudioAsset: TTS-generated narration audio
- VisualAsset: Generated visual content (PNG/JPEG/SVG)

API Models:
- Request/Response schemas for all endpoints
- Validation schemas for file uploads, job IDs, etc.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

# =============================================================================
# Enumerations
# =============================================================================


class JobStatus(str, Enum):
    """Job lifecycle states."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobPhase(str, Enum):
    """Current processing phase."""

    UPLOAD = "upload"
    SCRIPT = "script"
    AUDIO = "audio"
    VISUAL = "visual"
    COMPOSE = "compose"
    DONE = "done"


class VisualType(str, Enum):
    """Visual content type for scenes."""

    SLIDE = "slide"
    DIAGRAM = "diagram"
    GRAPH = "graph"
    FORMULA = "formula"
    CODE = "code"


class SceneStatus(str, Enum):
    """Scene processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# Core Entities
# =============================================================================


class AudioAsset(BaseModel):
    """TTS-generated narration audio for a scene."""

    asset_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # File metadata
    file_path: str
    file_size_bytes: int = 0
    format: str = "mp3"  # or "wav"

    # Audio properties
    duration_seconds: float = Field(..., gt=0.0)
    sample_rate: int | None = 22050  # Hz

    # Generation metadata
    tts_provider: str = "chatterbox"
    voice_id: str | None = None
    text_hash: str  # hash(narration_text + voice_id) for cache key

    # Timestamps
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, v: float) -> float:
        """Validate audio duration is positive."""
        if v <= 0:
            raise ValueError(f"Audio duration must be positive, got {v}")
        return v

    model_config = {"json_encoders": {datetime: lambda dt: dt.isoformat()}}


class VisualAsset(BaseModel):
    """Generated visual content (PNG/JPEG/SVG) for a scene."""

    asset_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # File metadata
    file_path: str
    file_size_bytes: int = 0
    format: str  # "png" | "jpeg" | "svg"

    # Visual properties
    width: int = 1280
    height: int = 720

    # Generation metadata
    visual_type: VisualType
    provider: str  # "presenton" | "graphviz" | "matplotlib" | "latex" | "pygments"
    prompt_hash: str  # hash(visual_type + prompt) for cache key

    # Error handling
    is_placeholder: bool = False  # True if fallback error image

    # Timestamps
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate visual format."""
        allowed = {"png", "jpeg", "svg"}
        if v not in allowed:
            raise ValueError(f"Format must be one of {allowed}, got {v}")
        return v

    model_config = {"json_encoders": {datetime: lambda dt: dt.isoformat()}}


class Scene(BaseModel):
    """Single segment of the output video (narration + visual)."""

    scene_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scene_index: int  # 0-based position in script

    # Content
    narration_text: str = Field(..., min_length=10, max_length=1000)
    visual_type: VisualType
    visual_prompt: str = Field(..., min_length=5, max_length=500)

    # Generated assets
    audio_asset: AudioAsset | None = None
    visual_asset: VisualAsset | None = None

    # Status
    status: SceneStatus = SceneStatus.PENDING
    error_message: str | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("narration_text")
    @classmethod
    def validate_narration_length(cls, v: str) -> str:
        """Validate narration text length."""
        if not (10 <= len(v) <= 1000):
            raise ValueError(f"Narration text length {len(v)} not in range [10, 1000]")
        return v

    @field_validator("visual_prompt")
    @classmethod
    def validate_prompt_length(cls, v: str) -> str:
        """Validate visual prompt length."""
        if not (5 <= len(v) <= 500):
            raise ValueError(f"Visual prompt length {len(v)} not in range [5, 500]")
        return v

    model_config = {"json_encoders": {datetime: lambda dt: dt.isoformat()}}


class Script(BaseModel):
    """Scene-based breakdown of the source document (3-7 scenes)."""

    scenes: list[Scene] = Field(..., min_length=3, max_length=7)
    fallback_used: bool = False  # True if LLM failed, generic script used
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    llm_provider: str | None = None  # e.g., "openai", "google"
    llm_model: str | None = None  # e.g., "gpt-4-turbo"

    @field_validator("scenes")
    @classmethod
    def validate_scene_count(cls, v: list[Scene]) -> list[Scene]:
        """Validate script has 3-7 scenes."""
        if not (3 <= len(v) <= 7):
            raise ValueError(f"Script must have 3-7 scenes, got {len(v)}")
        return v

    model_config = {"json_encoders": {datetime: lambda dt: dt.isoformat()}}


class Job(BaseModel):
    """Video generation request from upload through completion."""

    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.PENDING
    phase: JobPhase = JobPhase.UPLOAD

    # Input metadata
    source_file_name: str
    source_file_size: int  # bytes
    source_file_type: str  # "txt" | "pdf" | "md"
    document_text: str | None = None  # Extracted text content

    # Processing artifacts
    script: Script | None = None
    scenes: list[Scene] = Field(default_factory=list)

    # Output
    video_path: str | None = None
    video_url: str | None = None  # Pre-signed URL for S3
    video_duration: float | None = None  # seconds
    video_size_bytes: int | None = None
    video_fps: int | None = None  # Frame rate (24 for completed videos)
    video_resolution: str | None = None  # Resolution string "1280x720"

    # Error tracking
    errors: list[str] = Field(default_factory=list)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    # Flags
    is_cancelled: bool = False

    @field_validator("source_file_size")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        """Validate file size is within limits."""
        max_size = 50 * 1024 * 1024  # 50MB
        if v > max_size:
            raise ValueError(f"File size {v} exceeds maximum {max_size} bytes")
        return v

    @field_validator("source_file_type")
    @classmethod
    def validate_file_type(cls, v: str) -> str:
        """Validate file type is allowed."""
        allowed = {"txt", "pdf", "md"}
        if v not in allowed:
            raise ValueError(f"File type '{v}' not in allowed types: {allowed}")
        return v

    model_config = {"json_encoders": {datetime: lambda dt: dt.isoformat()}}


# =============================================================================
# API Request/Response Models
# =============================================================================


class VideoGenerateResponse(BaseModel):
    """Response for POST /api/v1/video/generate."""

    job_id: str
    status: JobStatus
    created_at: str  # ISO 8601 datetime

    @field_validator("job_id")
    @classmethod
    def validate_job_id(cls, v: str) -> str:
        """Validate job ID is a valid UUID."""
        try:
            uuid.UUID(v)
        except ValueError as e:
            raise ValueError("Job ID must be a valid UUID") from e
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "pending",
                "created_at": "2025-10-05T12:00:00Z",
            }
        }
    }


class VideoInfo(BaseModel):
    """Video metadata in job result."""

    video_url: str | None = None  # Optional - may not exist for failed/error jobs
    video_path: str | None = None
    duration_seconds: float | None = None
    size_bytes: int | None = None
    fps: int | None = 24
    resolution: str | None = "1280x720"
    format: str = "mp4"
    status: str | None = None  # "completed", "error", etc.
    error: str | None = None  # Error message if status is "error"


class JobResult(BaseModel):
    """Job result data for completed jobs."""

    video: VideoInfo | None = None  # Optional - may not exist for error states
    script_scenes: int | None = None  # Optional - count of scenes, not list
    successful_tasks: int | None = None
    failed_tasks: int | None = None
    processing_time_seconds: float | None = None
    script: dict | None = None  # Optional - full script data
    errors: list[str] | None = None  # Errors during processing


class JobStatusResponse(BaseModel):
    """Response for GET /api/v1/video/status/{job_id}."""

    job_id: str
    status: JobStatus
    phase: JobPhase | None = None
    message: str | None = None
    progress: int | None = Field(None, ge=0, le=100)
    created_at: str
    updated_at: str
    completed_at: str | None = None
    result: JobResult | None = None
    errors: list[str] | None = None

    @field_validator("job_id")
    @classmethod
    def validate_job_id(cls, v: str) -> str:
        """Validate job ID is a valid UUID."""
        try:
            uuid.UUID(v)
        except ValueError as e:
            raise ValueError("Job ID must be a valid UUID") from e
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "phase": "done",
                "message": "Video generated successfully",
                "progress": 100,
                "created_at": "2025-10-05T12:00:00Z",
                "updated_at": "2025-10-05T12:05:00Z",
                "completed_at": "2025-10-05T12:05:00Z",
                "result": {
                    "video": {
                        "video_url": "/api/v1/video/download/550e8400",
                        "duration_seconds": 45.5,
                        "size_bytes": 2048000,
                        "fps": 24,
                        "resolution": "1280x720",
                        "format": "mp4",
                    },
                    "script_scenes": 5,
                    "successful_tasks": 10,
                    "failed_tasks": 0,
                    "processing_time_seconds": 120.5,
                },
            }
        }
    }


class DependencyStatus(BaseModel):
    """Status of an external dependency."""

    status: str  # "up" | "down" | "circuit_open"
    latency_ms: float | None = None
    last_error: str | None = None


class HealthResponse(BaseModel):
    """Response for GET /health endpoint."""

    status: str  # "healthy" | "degraded" | "unhealthy"
    service: str = "text-to-video"
    dependencies: dict[str, Any]
    timestamp: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate health status value."""
        allowed = {"healthy", "degraded", "unhealthy"}
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}, got {v}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "service": "text-to-video",
                "dependencies": {
                    "tts_service": {"status": "up", "latency_ms": 45.2},
                    "llm_service": {"status": "up", "latency_ms": 123.5},
                },
                "timestamp": "2025-10-05T12:00:00Z",
            }
        }
    }


# =============================================================================
# File Upload Validation
# =============================================================================


class FileUploadValidator:
    """Utility class for file upload validation."""

    @staticmethod
    def validate_file_format(filename: str, content_type: str) -> None:
        """
        Validate file format and content type.

        Args:
            filename: Name of the uploaded file
            content_type: MIME type of the uploaded file

        Raises:
            ValueError: If file format or content type is invalid
        """
        if not filename:
            raise ValueError("Filename is required")

        # Check file extension
        allowed_extensions = {".txt", ".pdf", ".md"}
        file_ext = filename.lower()
        if not any(file_ext.endswith(ext) for ext in allowed_extensions):
            raise ValueError(f"Invalid file type. Allowed: {', '.join(allowed_extensions)}")

        # Check content type
        allowed_content_types = {"text/plain", "application/pdf", "text/markdown"}
        if content_type and content_type not in allowed_content_types:
            raise ValueError(f"Invalid content type. Allowed: {', '.join(allowed_content_types)}")

    @staticmethod
    def validate_file_size(size: int, max_size: int = 50 * 1024 * 1024) -> None:
        """
        Validate file size is within limits.

        Args:
            size: File size in bytes
            max_size: Maximum allowed size in bytes (default: 50MB)

        Raises:
            ValueError: If file size exceeds maximum
        """
        if size > max_size:
            max_mb = max_size // (1024 * 1024)
            raise ValueError(f"File too large. Maximum size: {max_mb}MB")
