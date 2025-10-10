"""
Error schemas and custom exceptions for the Text-to-Video service.

This module defines:
- Custom HTTP exceptions
- Error response models
- Error codes and messages
"""

from typing import Any

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Detailed error information."""

    code: str
    message: str
    field: str | None = None
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: str  # Error type
    message: str  # Human-readable message
    details: list[ErrorDetail] | None = None
    job_id: str | None = None


# =============================================================================
# Custom HTTP Exceptions
# =============================================================================


class ServiceException(Exception):
    """Base exception for service errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class FileValidationError(ServiceException):
    """Raised when file validation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="FILE_VALIDATION_ERROR",
            details=details,
        )


class JobNotFoundError(ServiceException):
    """Raised when job is not found."""

    def __init__(self, job_id: str):
        super().__init__(
            message=f"Job not found: {job_id}",
            status_code=404,
            error_code="JOB_NOT_FOUND",
            details={"job_id": job_id},
        )


class VideoNotReadyError(ServiceException):
    """Raised when video is not ready for download."""

    def __init__(self, job_id: str, current_status: str):
        super().__init__(
            message=f"Video not ready. Current status: {current_status}",
            status_code=400,
            error_code="VIDEO_NOT_READY",
            details={"job_id": job_id, "status": current_status},
        )


class VideoNotFoundError(ServiceException):
    """Raised when video file is not found."""

    def __init__(self, job_id: str):
        super().__init__(
            message=f"Video file not found for job: {job_id}",
            status_code=404,
            error_code="VIDEO_NOT_FOUND",
            details={"job_id": job_id},
        )


class JobProcessingError(ServiceException):
    """Raised when job processing fails."""

    def __init__(self, job_id: str, message: str):
        super().__init__(
            message=f"Job processing failed: {message}",
            status_code=500,
            error_code="JOB_PROCESSING_ERROR",
            details={"job_id": job_id},
        )


class ExternalServiceError(ServiceException):
    """Raised when external service fails."""

    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"{service} service error: {message}",
            status_code=503,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service},
        )


class ResourceLimitError(ServiceException):
    """Raised when resource limit is exceeded."""

    def __init__(self, resource: str, limit: str):
        super().__init__(
            message=f"{resource} limit exceeded: {limit}",
            status_code=429,
            error_code="RESOURCE_LIMIT_ERROR",
            details={"resource": resource, "limit": limit},
        )


# =============================================================================
# Error Code Constants
# =============================================================================

ERROR_CODES = {
    "FILE_VALIDATION_ERROR": "Invalid file upload",
    "JOB_NOT_FOUND": "Job not found",
    "VIDEO_NOT_READY": "Video not ready for download",
    "VIDEO_NOT_FOUND": "Video file not found",
    "JOB_PROCESSING_ERROR": "Job processing failed",
    "EXTERNAL_SERVICE_ERROR": "External service unavailable",
    "RESOURCE_LIMIT_ERROR": "Resource limit exceeded",
    "INTERNAL_ERROR": "Internal server error",
}
