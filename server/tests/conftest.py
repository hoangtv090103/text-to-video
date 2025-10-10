"""
Pytest configuration and shared fixtures for the Text-to-Video service.

This module provides:
- Test fixtures for FastAPI app, async client, mock services
- Sample data fixtures for documents, jobs, scripts, scenes
- Cleanup utilities for temporary files
"""

import asyncio
import tempfile
import uuid
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def app() -> AsyncGenerator[FastAPI, None]:
    """
    Create a FastAPI app instance for testing.

    This imports the actual app but mocks external dependencies
    to avoid requiring TTS/LLM services during tests.
    """
    # Mock the health checks to avoid startup failures
    from unittest.mock import patch

    # Mock external service health checks
    with (
        patch("app.main.check_tts_health", return_value=True),
        patch("app.main.check_llm_health", return_value=True),
    ):
        # Import app after mocking to avoid startup issues
        from app.main import app as fastapi_app

        yield fastapi_app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing the API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_txt_content() -> str:
    """Sample TXT document content for testing."""
    return """
# Introduction to Machine Learning

Machine learning is a subset of artificial intelligence that enables systems to learn
and improve from experience without being explicitly programmed.

## Key Concepts

1. **Supervised Learning**: Learning from labeled data
2. **Unsupervised Learning**: Finding patterns in unlabeled data
3. **Reinforcement Learning**: Learning through rewards and penalties

## Applications

Machine learning powers many modern applications:
- Speech recognition
- Image classification
- Recommendation systems
- Autonomous vehicles

## Conclusion

The field continues to evolve rapidly with new techniques and applications emerging.
    """.strip()


@pytest.fixture
def sample_job_id() -> str:
    """Generate a sample job ID."""
    return str(uuid.uuid4())


@pytest.fixture
def mock_tts_response() -> dict[str, str | float]:
    """Mock TTS service response."""
    return {
        "audio_url": "http://tts-service/audio/test.mp3",
        "duration": 12.5,
        "format": "mp3",
    }


@pytest.fixture
def mock_llm_script_response() -> dict[str, list[dict[str, str | int]] | bool]:
    """Mock LLM service script generation response."""
    return {
        "scenes": [
            {
                "scene_index": 1,
                "narration_text": "Introduction to the topic with key concepts.",
                "visual_type": "slide",
                "visual_prompt": "Title slide with main heading",
            },
            {
                "scene_index": 2,
                "narration_text": "Detailed explanation of the core concepts.",
                "visual_type": "diagram",
                "visual_prompt": "Flowchart showing process steps",
            },
            {
                "scene_index": 3,
                "narration_text": "Summary and key takeaways.",
                "visual_type": "slide",
                "visual_prompt": "Summary slide with bullet points",
            },
        ],
        "fallback_used": False,
    }


# Note: Additional fixtures for Job, Scene, Script, AudioAsset, VisualAsset
# will be uncommented once the schemas are implemented in T021

# Async fixtures for FastAPI testing will be added after T025


@pytest_asyncio.fixture
async def seed_test_jobs():
    """
    Seed the job store with test jobs for contract tests.

    Creates:
    - Pending job: 0f39f6d8-362c-4870-ac97-cc8367c61d41
    - Completed job: 00000000-0000-4000-8000-000000000001 (was: completed-test-job-uuid)
    - Processing job: 00000000-0000-4000-8000-000000000002 (was: processing-test-job-uuid)
    - Failed job: 00000000-0000-4000-8000-000000000003 (was: failed-test-job-uuid)
    """
    from datetime import UTC, datetime

    from app.services.job_service import job_service

    # Create pending job
    pending_job_id = "0f39f6d8-362c-4870-ac97-cc8367c61d41"
    now = datetime.now(UTC).isoformat()

    await job_service.initialize_job(job_id=pending_job_id, message="Pending test job", progress=10)

    # Update job with additional data
    job_data = await job_service.get_job_status(pending_job_id)
    if job_data:
        job_data.update(
            {
                "job_id": pending_job_id,
                "status": "pending",
                "phase": "upload",
                "created_at": now,
                "updated_at": now,
                "file_name": "test.txt",
                "file_size": 100,
                "file_type": "txt",
            }
        )

    # Create completed job (using valid UUID format)
    completed_job_id = "00000000-0000-4000-8000-000000000001"

    await job_service.initialize_job(
        job_id=completed_job_id, message="Completed test job", progress=100
    )

    # Update job with completion data
    job_data = await job_service.get_job_status(completed_job_id)
    if job_data:
        job_data.update(
            {
                "job_id": completed_job_id,
                "status": "completed",
                "phase": "done",
                "created_at": now,
                "updated_at": now,
                "completed_at": now,
                "file_name": "test.txt",
                "file_size": 100,
                "file_type": "txt",
            }
        )

    # Set the job result with video path
    await job_service.set_job_result(
        job_id=completed_job_id,
        result_data={
            "video": {
                "video_path": f"/tmp/videos/{completed_job_id}.mp4",
                "video_url": f"/api/v1/video/download/{completed_job_id}",
                "duration": 10.5,
                "file_size": 1056,
            },
            "script": {"total_scenes": 3, "scenes": []},
            "script_scenes": 3,
            "successful_tasks": 6,
            "failed_tasks": 0,
        },
    )

    # Create processing job (using valid UUID format)
    processing_job_id = "00000000-0000-4000-8000-000000000002"

    await job_service.initialize_job(
        job_id=processing_job_id, message="Processing test job", progress=50
    )

    # Update job with processing status
    job_data = await job_service.get_job_status(processing_job_id)
    if job_data:
        job_data.update(
            {
                "job_id": processing_job_id,
                "status": "processing",
                "phase": "generating",
                "created_at": now,
                "updated_at": now,
                "file_name": "test.txt",
                "file_size": 100,
                "file_type": "txt",
            }
        )

    # Create failed job (using valid UUID format)
    failed_job_id = "00000000-0000-4000-8000-000000000003"

    await job_service.initialize_job(job_id=failed_job_id, message="Failed test job", progress=30)

    # Update job with failed status
    job_data = await job_service.get_job_status(failed_job_id)
    if job_data:
        job_data.update(
            {
                "job_id": failed_job_id,
                "status": "failed",
                "phase": "error",
                "created_at": now,
                "updated_at": now,
                "file_name": "test.txt",
                "file_size": 100,
                "file_type": "txt",
                "error": "Test error",
            }
        )

    yield

    # Cleanup is handled by job_service


@pytest.fixture
def create_test_video():
    """
    Create a test video file for download/stream tests.

    Creates a minimal valid MP4 file at /tmp/videos/00000000-0000-4000-8000-000000000001.mp4
    (matching the completed job UUID from seed_test_jobs)
    """
    from pathlib import Path

    video_dir = Path("/tmp/videos")
    video_dir.mkdir(parents=True, exist_ok=True)

    video_path = video_dir / "00000000-0000-4000-8000-000000000001.mp4"

    # Create a minimal MP4 file (just a header, not a valid playable video but enough for tests)
    # This is a minimal MP4 header - real video creation would need ffmpeg/MoviePy
    mp4_header = bytes(
        [
            0x00,
            0x00,
            0x00,
            0x20,
            0x66,
            0x74,
            0x79,
            0x70,
            0x69,
            0x73,
            0x6F,
            0x6D,
            0x00,
            0x00,
            0x02,
            0x00,
            0x69,
            0x73,
            0x6F,
            0x6D,
            0x69,
            0x73,
            0x6F,
            0x32,
            0x6D,
            0x70,
            0x34,
            0x31,
            0x00,
            0x00,
            0x00,
            0x08,
        ]
    )

    with open(video_path, "wb") as f:
        f.write(mp4_header)
        # Write some dummy data to make it non-empty
        f.write(b"\x00" * 1024)

    yield video_path

    # Cleanup
    if video_path.exists():
        video_path.unlink()
