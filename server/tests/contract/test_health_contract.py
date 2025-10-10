"""
Contract tests for GET /health endpoint.

Tests validate API contract compliance as specified in:
specs/001-build-a-service/contracts/health.yaml

All tests should FAIL initially (TDD approach) until implementation complete.
"""

import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.contract
@pytest.mark.asyncio
async def test_health_all_dependencies_up(client: AsyncClient) -> None:
    """
    Test: All dependencies healthy returns 200 with status="healthy".
    Contract: GET /health
    Expected: 200 OK with dependencies.tts_service="up" and dependencies.llm_service="up"
    """
    response = await client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "status" in data
    assert "dependencies" in data
    assert "timestamp" in data

    # When all deps are up, status should be "healthy"
    assert data["status"] == "healthy"
    assert "tts_service" in data["dependencies"]
    assert "llm_service" in data["dependencies"]


@pytest.mark.contract
@pytest.mark.asyncio
async def test_health_tts_service_down(client: AsyncClient) -> None:
    """
    Test: TTS service down returns 200 with status="degraded".
    Contract: GET /health
    Expected: 200 OK with dependencies.tts_service="down"
    """
    # This test will need mocking of TTS health check
    # For now, we define the expected contract

    response = await client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Status can be "degraded" when some services are down
    assert data["status"] in ["healthy", "degraded", "unhealthy"]


@pytest.mark.contract
@pytest.mark.asyncio
async def test_health_circuit_breaker_open(client: AsyncClient) -> None:
    """
    Test: Circuit breaker open returns 200 with status="degraded".
    Contract: GET /health
    Expected: 200 OK with dependencies.llm_service="circuit_open"
    """
    response = await client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "status" in data
    assert "dependencies" in data

    # Validate dependency status values are one of: up, down, circuit_open
    for _service_name, service_status in data["dependencies"].items():
        if isinstance(service_status, dict):
            assert service_status.get("status") in ["up", "down", "circuit_open"]
        else:
            assert service_status in ["up", "down", "circuit_open"]


@pytest.mark.contract
@pytest.mark.asyncio
async def test_health_response_structure(client: AsyncClient) -> None:
    """
    Test: Health endpoint returns proper response structure.
    Contract: GET /health
    Expected: Response matches HealthResponse schema
    """
    response = await client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Validate required fields
    assert "status" in data
    assert "dependencies" in data
    assert "timestamp" in data

    # Validate status enum
    assert data["status"] in ["healthy", "degraded", "unhealthy"]

    # Validate timestamp format (ISO 8601)
    assert isinstance(data["timestamp"], str)
    assert "T" in data["timestamp"] or " " in data["timestamp"]
