"""
Integration tests configuration - Tests against real running server.
No mocks, all services must be running.
"""
import os
import sys
import asyncio
import pytest
import httpx
from typing import Dict, Any

# Configuration
BASE_URL = os.getenv("TEST_SERVER_URL", "http://localhost:8000")
TTS_URL = os.getenv("TTS_SERVICE_URL", "http://localhost:4123")
LLM_URL = os.getenv("LLM_URL", "http://localhost:11434")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Test parameters
TEST_TIMEOUT = 300  # 5 minutes
MAX_WAIT_TIME = 600  # 10 minutes for job completion
POLL_INTERVAL = 2  # Check job status every 2 seconds


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_pdf_path():
    """Path to the test PDF document."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '2507.08034v1.pdf'))


@pytest.fixture
def test_pdf_content(test_pdf_path):
    """Load test PDF content as bytes."""
    if os.path.exists(test_pdf_path):
        with open(test_pdf_path, 'rb') as f:
            return f.read()
    else:
        raise FileNotFoundError(f"Test PDF not found at {test_pdf_path}")


@pytest.fixture
async def http_client():
    """Create an HTTP client for API requests."""
    async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
        yield client


@pytest.fixture
def reports_dir():
    """Ensure reports directory exists."""
    reports_path = os.path.join(os.path.dirname(__file__), 'reports')
    os.makedirs(reports_path, exist_ok=True)
    return reports_path


@pytest.fixture(scope="session")
async def verify_services_running():
    """Verify all required services are running before tests."""
    print("\n" + "="*80)
    print("Verifying Required Services")
    print("="*80)
    
    services = {
        "Server": f"{BASE_URL}/api/v1/health",
        "TTS": f"{TTS_URL}/health",
    }
    
    async with httpx.AsyncClient(timeout=10) as client:
        all_running = True
        for service_name, url in services.items():
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    print(f"✓ {service_name}: Running")
                else:
                    print(f"✗ {service_name}: Not responding properly (status {response.status_code})")
                    all_running = False
            except Exception as e:
                print(f"✗ {service_name}: Not accessible - {e}")
                all_running = False
        
        if not all_running:
            pytest.skip("Not all required services are running. See README.md for setup instructions.")
        
        print("="*80 + "\n")


async def wait_for_job_completion(
    client: httpx.AsyncClient,
    job_id: str,
    max_wait: int = MAX_WAIT_TIME,
    poll_interval: int = POLL_INTERVAL
) -> Dict[str, Any]:
    """
    Wait for a job to complete and return its final status.
    
    Args:
        client: HTTP client
        job_id: Job ID to monitor
        max_wait: Maximum time to wait in seconds
        poll_interval: How often to check status in seconds
    
    Returns:
        Final job status dictionary
    
    Raises:
        TimeoutError: If job doesn't complete within max_wait
    """
    start_time = asyncio.get_event_loop().time()
    
    while True:
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > max_wait:
            raise TimeoutError(f"Job {job_id} did not complete within {max_wait}s")
        
        response = await client.get(f"{BASE_URL}/api/v1/video/jobs/{job_id}")
        if response.status_code != 200:
            raise Exception(f"Failed to get job status: {response.status_code}")
        
        job_data = response.json()
        status = job_data.get("status", "unknown")
        
        if status in ["completed", "failed", "cancelled"]:
            return job_data
        
        await asyncio.sleep(poll_interval)


def calculate_statistics(values: list) -> Dict[str, float]:
    """Calculate statistical metrics from a list of values."""
    if not values:
        return {"min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}
    
    sorted_values = sorted(values)
    n = len(sorted_values)
    
    return {
        "min": sorted_values[0],
        "max": sorted_values[-1],
        "avg": sum(sorted_values) / n,
        "p50": sorted_values[int(n * 0.50)],
        "p95": sorted_values[int(n * 0.95)] if n > 1 else sorted_values[-1],
        "p99": sorted_values[int(n * 0.99)] if n > 1 else sorted_values[-1],
    }
