from pydantic import BaseModel, validator, Field
from fastapi import File, UploadFile
from typing import Optional, Any, Dict
from enum import Enum
import uuid


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FileUploadValidator:
    """Custom validator for file uploads."""

    @staticmethod
    def validate_file_format(filename: str, content_type: str) -> None:
        """Validate file format and content type."""
        if not filename:
            raise ValueError("Filename is required")

        # Check file extension
        allowed_extensions = {'.txt', '.pdf', '.md'}
        file_ext = filename.lower()
        if not any(file_ext.endswith(ext) for ext in allowed_extensions):
            raise ValueError(f"Invalid file type. Allowed: {', '.join(allowed_extensions)}")

        # Check content type
        allowed_content_types = {'text/plain', 'application/pdf', 'text/markdown'}
        if content_type and content_type not in allowed_content_types:
            raise ValueError(f"Invalid content type. Allowed: {', '.join(allowed_content_types)}")

    @staticmethod
    def validate_file_size(size: int, max_size: int = 50 * 1024 * 1024) -> None:
        """Validate file size."""
        if size > max_size:
            max_mb = max_size // (1024 * 1024)
            raise ValueError(f"File too large. Maximum size: {max_mb}MB")


class JobIdValidator:
    """Custom validator for job IDs."""

    @staticmethod
    def validate_job_id_format(job_id: str) -> None:
        """Validate job ID format (UUID)."""
        if not job_id:
            raise ValueError("Job ID is required")

        try:
            uuid.UUID(job_id)
        except ValueError:
            raise ValueError("Job ID must be a valid UUID")


class GenerateVideoRequest(BaseModel):
    """Request model for video generation with file upload."""

    file: UploadFile = File(...)

    @validator('file')
    def validate_file_upload(cls, v):
        """Validate the uploaded file."""
        if not v:
            raise ValueError("File is required")

        # Validate filename and content type
        FileUploadValidator.validate_file_format(v.filename or "", v.content_type or "")

        # Validate file size if available
        if v.size:
            FileUploadValidator.validate_file_size(v.size)

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "file": {
                    "filename": "example.pdf",
                    "content_type": "application/pdf",
                    "size": 1024000
                }
            }
        }


class JobStatusResponse(BaseModel):
    """Response model for job status with comprehensive validation."""

    job_id: str = Field(..., min_length=36, max_length=36, description="UUID4 job identifier")
    status: JobStatus = Field(..., description="Current job status")
    message: Optional[str] = Field(None, description="Status message")
    progress: Optional[int] = Field(None, ge=0, le=100, description="Progress percentage (0-100)")
    updated_at: Optional[str] = Field(None, description="ISO timestamp of last update")
    completed_at: Optional[str] = Field(None, description="ISO timestamp of completion")
    result: Optional[Dict[str, Any]] = Field(None, description="Job result data")

    @validator('job_id')
    def validate_job_id(cls, v):
        """Validate job ID format."""
        JobIdValidator.validate_job_id_format(v)
        return v

    @validator('updated_at', 'completed_at')
    def validate_timestamp(cls, v):
        """Validate timestamp format (basic check)."""
        if v:
            # Basic ISO format validation
            if not isinstance(v, str) or len(v) < 19:
                raise ValueError("Invalid timestamp format")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "processing",
                "message": "Generating audio and visual assets",
                "progress": 65,
                "updated_at": "2024-01-01T12:00:00Z",
                "completed_at": None,
                "result": None
            }
        }


class VideoGenerationResult(BaseModel):
    """Detailed result model for video generation."""

    job_id: str
    status: JobStatus
    message: str
    processing_time: float
    total_scenes: int
    successful_tasks: int
    failed_tasks: int
    scenes: list
    script_scenes: list
    video: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @validator('job_id')
    def validate_job_id(cls, v):
        """Validate job ID format."""
        JobIdValidator.validate_job_id_format(v)
        return v

    @validator('processing_time')
    def validate_processing_time(cls, v):
        """Validate processing time is positive."""
        if v < 0:
            raise ValueError("Processing time must be positive")
        return v
