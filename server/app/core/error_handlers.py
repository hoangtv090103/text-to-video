"""
FastAPI exception handlers for custom errors.

This module registers exception handlers that convert custom
exceptions into properly formatted JSON error responses.
"""

import logging
from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.schemas.errors import (
    ErrorResponse,
    ExternalServiceError,
    FileValidationError,
    JobNotFoundError,
    JobProcessingError,
    ResourceLimitError,
    ServiceException,
    VideoNotFoundError,
    VideoNotReadyError,
)

logger = logging.getLogger(__name__)


async def service_exception_handler(request: Request, exc: ServiceException) -> JSONResponse:
    """
    Handle ServiceException and its subclasses.

    Args:
        request: FastAPI request
        exc: ServiceException instance

    Returns:
        JSON error response
    """
    # Log the error
    logger.error(
        f"{exc.error_code}: {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
            "path": request.url.path,
        },
    )

    # Build error response
    error_response = ErrorResponse(
        error=exc.error_code,
        message=exc.message,
        details=None,
        job_id=exc.details.get("job_id") if exc.details else None,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
    )


async def file_validation_error_handler(request: Request, exc: FileValidationError) -> JSONResponse:
    """Handle file validation errors."""
    return await service_exception_handler(request, exc)


async def job_not_found_error_handler(request: Request, exc: JobNotFoundError) -> JSONResponse:
    """Handle job not found errors."""
    return await service_exception_handler(request, exc)


async def video_not_ready_error_handler(request: Request, exc: VideoNotReadyError) -> JSONResponse:
    """Handle video not ready errors."""
    return await service_exception_handler(request, exc)


async def video_not_found_error_handler(request: Request, exc: VideoNotFoundError) -> JSONResponse:
    """Handle video not found errors."""
    return await service_exception_handler(request, exc)


async def job_processing_error_handler(request: Request, exc: JobProcessingError) -> JSONResponse:
    """Handle job processing errors."""
    return await service_exception_handler(request, exc)


async def external_service_error_handler(
    request: Request, exc: ExternalServiceError
) -> JSONResponse:
    """Handle external service errors."""
    return await service_exception_handler(request, exc)


async def resource_limit_error_handler(request: Request, exc: ResourceLimitError) -> JSONResponse:
    """Handle resource limit errors."""
    return await service_exception_handler(request, exc)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle generic unhandled exceptions.

    Args:
        request: FastAPI request
        exc: Exception instance

    Returns:
        JSON error response
    """
    logger.exception(
        f"Unhandled exception: {exc}",
        extra={
            "exception_type": type(exc).__name__,
            "path": request.url.path,
        },
    )

    error_response = ErrorResponse(
        error="INTERNAL_ERROR",
        message="An unexpected error occurred",
        details=None,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
    )


async def validation_exception_handler(request: Request, exc: Any) -> JSONResponse:
    """
    Handle Pydantic ValidationError from FastAPI.

    Args:
        request: FastAPI request
        exc: ValidationError instance

    Returns:
        JSON error response
    """
    logger.warning(
        f"Validation error: {exc}",
        extra={
            "path": request.url.path,
            "errors": exc.errors() if hasattr(exc, "errors") else str(exc),
        },
    )

    error_response = ErrorResponse(
        error="VALIDATION_ERROR",
        message="Invalid request data",
        details=None,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(),
    )


def register_exception_handlers(app):
    """
    Register all exception handlers with FastAPI app.

    Args:
        app: FastAPI application instance
    """
    # Custom service exceptions
    app.add_exception_handler(ServiceException, service_exception_handler)
    app.add_exception_handler(FileValidationError, file_validation_error_handler)
    app.add_exception_handler(JobNotFoundError, job_not_found_error_handler)
    app.add_exception_handler(VideoNotReadyError, video_not_ready_error_handler)
    app.add_exception_handler(VideoNotFoundError, video_not_found_error_handler)
    app.add_exception_handler(JobProcessingError, job_processing_error_handler)
    app.add_exception_handler(ExternalServiceError, external_service_error_handler)
    app.add_exception_handler(ResourceLimitError, resource_limit_error_handler)

    # Generic exceptions
    app.add_exception_handler(Exception, generic_exception_handler)

    # FastAPI validation errors
    from fastapi.exceptions import RequestValidationError

    app.add_exception_handler(RequestValidationError, validation_exception_handler)
