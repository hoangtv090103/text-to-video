from pydantic import BaseModel
from fastapi import File, UploadFile, HTTPException
from typing import Optional, Any, Dict
import uuid


class GenerateVideoRequest(BaseModel):
    file: UploadFile = File(...)

    class Config:
        json_schema_extra = {
            "example": {
                "file": {
                    "filename": "example.pdf",
                    "content_type": "application/pdf"
                }
            }
        }


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    message: Optional[str] = None
    progress: Optional[int] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "processing",
                "message": "Generating audio and visual assets",
                "progress": 65,
                "updated_at": "2024-01-01T12:00:00Z"
            }
        }


# File validation constants
ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.md'}
ALLOWED_CONTENT_TYPES = {
    'text/plain', 'application/pdf', 'text/markdown', 
    'text/x-markdown', 'application/x-pdf'
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_file_upload(file: UploadFile) -> None:
    """
    Validate uploaded file format, size, and content type.
    
    Args:
        file: The uploaded file to validate
        
    Raises:
        HTTPException: If validation fails
    """
    # Check file extension
    if file.filename:
        ext = '.' + file.filename.split('.')[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File format not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )
    
    # Check content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Content type not supported. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}"
        )

def validate_job_id(job_id: str) -> None:
    """
    Validate job ID format.
    
    Args:
        job_id: The job ID to validate
        
    Raises:
        HTTPException: If job ID format is invalid
    """
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid job ID format. Must be a valid UUID."
        )
