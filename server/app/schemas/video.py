from pydantic import BaseModel
from fastapi import File, UploadFile
from typing import Optional, Any, Dict


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
