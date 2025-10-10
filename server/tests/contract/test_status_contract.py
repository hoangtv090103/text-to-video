"""
Contract tests for GET /api/v1/video/status/{job_id} endpoint.

Tests validate API contract compliance as specified in:
specs/001-build-a-service/contracts/status.yaml

All tests should FAIL initially (TDD approach) until implementation complete.
"""

import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.contract
@pytest.mark.asyncio
async def test_status_pending_job(client: AsyncClient, seed_test_jobs) -> None:
    """
    Test: Valid job_id (pending status) returns 200 with JobStatusResponse.
    Contract: GET /api/v1/video/status/{job_id}
    Expected: 200 OK with status, progress, timestamps
    """
    # Use the seeded pending job
    job_id = "0f39f6d8-362c-4870-ac97-cc8367c61d41"
    response = await client.get(f"/api/v1/video/status/{job_id}")

    # Expected to fail until endpoint is implemented
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "job_id" in data
    assert "status" in data
    assert data["status"] in ["pending", "processing", "completed", "failed", "cancelled"]


@pytest.mark.contract
@pytest.mark.asyncio
async def test_status_completed_job(client: AsyncClient, seed_test_jobs) -> None:
    """
    Test: Completed job returns 200 with result.video.video_url.
    Contract: GET /api/v1/video/status/{job_id}
    Expected: 200 OK with video_url in result
    """
    # Use a known completed job_id (mocked in fixture)
    completed_job_id = "00000000-0000-4000-8000-000000000001"

    response = await client.get(f"/api/v1/video/status/{completed_job_id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["status"] == "completed"
    assert "result" in data
    assert "video" in data["result"]
    assert "video_url" in data["result"]["video"]


@pytest.mark.contract
@pytest.mark.asyncio
async def test_status_invalid_uuid(client: AsyncClient) -> None:
    """
    Test: Invalid UUID format returns 422 validation error.
    Contract: GET /api/v1/video/status/{job_id}
    Expected: 422 Unprocessable Entity
    """
    invalid_job_id = "not-a-valid-uuid"

    response = await client.get(f"/api/v1/video/status/{invalid_job_id}")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.contract
@pytest.mark.asyncio
async def test_status_nonexistent_job(client: AsyncClient) -> None:
    """
    Test: Non-existent job_id returns 404 "Job not found".
    Contract: GET /api/v1/video/status/{job_id}
    Expected: 404 Not Found
    """
    nonexistent_job_id = "12345678-1234-1234-1234-123456789abc"

    response = await client.get(f"/api/v1/video/status/{nonexistent_job_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "not found" in data.get("detail", "").lower()
