"""
Contract tests for GET /api/v1/video/download/{job_id} endpoint.

Tests validate API contract compliance as specified in:
specs/001-build-a-service/contracts/download.yaml

All tests should FAIL initially (TDD approach) until implementation complete.
"""

import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.contract
@pytest.mark.asyncio
async def test_download_completed_job_with_attachment(
    client: AsyncClient, seed_test_jobs, create_test_video
) -> None:
    """
    Test: Completed job with download=true returns 200 with Content-Disposition attachment.
    Contract: GET /api/v1/video/download/{job_id}?download=true
    Expected: 200 OK with video/mp4 content and attachment header
    """
    completed_job_id = "00000000-0000-4000-8000-000000000001"

    response = await client.get(
        f"/api/v1/video/download/{completed_job_id}",
        params={"download": "true"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] in ["video/mp4", "application/octet-stream"]
    assert "attachment" in response.headers.get("content-disposition", "").lower()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_download_completed_job_streaming(
    client: AsyncClient, seed_test_jobs, create_test_video
) -> None:
    """
    Test: Completed job with download=false returns 200 streaming video.
    Contract: GET /api/v1/video/download/{job_id}?download=false
    Expected: 200 OK with video/mp4 content, inline disposition
    """
    completed_job_id = "00000000-0000-4000-8000-000000000001"

    response = await client.get(
        f"/api/v1/video/download/{completed_job_id}",
        params={"download": "false"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert "video/mp4" in response.headers["content-type"]


@pytest.mark.contract
@pytest.mark.asyncio
async def test_download_job_still_processing(client: AsyncClient, seed_test_jobs) -> None:
    """
    Test: Job still processing returns 400 "not ready".
    Contract: GET /api/v1/video/download/{job_id}
    Expected: 400 Bad Request
    """
    processing_job_id = "00000000-0000-4000-8000-000000000002"

    response = await client.get(f"/api/v1/video/download/{processing_job_id}")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert (
        "not ready" in data.get("detail", "").lower()
        or "not completed" in data.get("detail", "").lower()
    )


@pytest.mark.contract
@pytest.mark.asyncio
async def test_download_job_failed(client: AsyncClient, seed_test_jobs) -> None:
    """
    Test: Failed job returns 404 "no video available".
    Contract: GET /api/v1/video/download/{job_id}
    Expected: 404 Not Found
    """
    failed_job_id = "00000000-0000-4000-8000-000000000003"

    response = await client.get(f"/api/v1/video/download/{failed_job_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    detail = data.get("detail", "").lower()
    assert "no video" in detail or "not found" in detail


@pytest.mark.contract
@pytest.mark.asyncio
async def test_download_nonexistent_job(client: AsyncClient) -> None:
    """
    Test: Non-existent job returns 404 "Job not found".
    Contract: GET /api/v1/video/download/{job_id}
    Expected: 404 Not Found
    """
    nonexistent_job_id = "12345678-1234-1234-1234-123456789abc"

    response = await client.get(f"/api/v1/video/download/{nonexistent_job_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
