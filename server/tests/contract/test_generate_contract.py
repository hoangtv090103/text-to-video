"""
Contract tests for POST /api/v1/video/generate endpoint.

Tests validate API contract compliance as specified in:
specs/001-build-a-service/contracts/generate.yaml

All tests should FAIL initially (TDD approach) until T021-T028 are implemented.
"""

import io

import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.contract
@pytest.mark.asyncio
async def test_generate_video_valid_txt_upload(client: AsyncClient) -> None:
    """
    Test: Valid TXT file upload returns 202 with job_id, status, created_at.
    Contract: POST /api/v1/video/generate
    Expected: 202 Accepted with job metadata
    """
    # Create a valid TXT file
    file_content = b"Sample document text for video generation"
    files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}

    response = await client.post("/api/v1/video/generate", files=files)

    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()

    # Validate response schema
    assert "job_id" in data
    assert "status" in data
    assert "created_at" in data

    # Validate job_id is a valid UUID
    assert len(data["job_id"]) == 36
    assert data["status"] == "pending"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_generate_video_valid_pdf_upload(client: AsyncClient) -> None:
    """
    Test: Valid PDF file upload returns 202.
    Contract: POST /api/v1/video/generate
    """
    file_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj"
    files = {"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}

    response = await client.post("/api/v1/video/generate", files=files)

    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()
    assert data["status"] == "pending"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_generate_video_valid_md_upload(client: AsyncClient) -> None:
    """
    Test: Valid Markdown file upload returns 202.
    Contract: POST /api/v1/video/generate
    """
    file_content = b"# Sample Markdown\n\nThis is a test document."
    files = {"file": ("test.md", io.BytesIO(file_content), "text/markdown")}

    response = await client.post("/api/v1/video/generate", files=files)

    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()
    assert data["status"] == "pending"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_generate_video_file_too_large(client: AsyncClient) -> None:
    """
    Test: File >50MB returns 400 or 413 with error message.
    Contract: POST /api/v1/video/generate
    Expected: 400 Bad Request or 413 Request Entity Too Large with "exceeds 50MB limit"
    """
    # Create a 51MB file (exceeds limit)
    large_content = b"x" * (51 * 1024 * 1024)
    files = {"file": ("large.txt", io.BytesIO(large_content), "text/plain")}

    response = await client.post("/api/v1/video/generate", files=files)

    # Accept both 400 (Bad Request) and 413 (Request Entity Too Large)
    assert response.status_code in [
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    ]
    data = response.json()
    assert "50MB" in data.get("detail", "").lower() or "50mb" in data.get("detail", "").lower()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_generate_video_unsupported_file_type(client: AsyncClient) -> None:
    """
    Test: Unsupported file type (.docx) returns 400 with error.
    Contract: POST /api/v1/video/generate
    Expected: 400 Bad Request with "unsupported format"
    """
    file_content = b"Fake DOCX content"
    files = {
        "file": (
            "test.docx",
            io.BytesIO(file_content),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }

    response = await client.post("/api/v1/video/generate", files=files)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    detail = data.get("detail", "").lower()
    assert "unsupported" in detail or "invalid" in detail or "format" in detail


@pytest.mark.contract
@pytest.mark.asyncio
async def test_generate_video_missing_file(client: AsyncClient) -> None:
    """
    Test: Missing file parameter returns 422 validation error.
    Contract: POST /api/v1/video/generate
    Expected: 422 Unprocessable Entity
    """
    response = await client.post("/api/v1/video/generate", files={})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
