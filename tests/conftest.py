"""
Shared test fixtures and configurations for the text-to-video testing suite.
"""
import os
import sys
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any

# Set environment variables BEFORE importing app modules
# This prevents initialization errors when modules are loaded
os.environ.setdefault('OPENAI_API_KEY', 'test-key-for-testing')
os.environ.setdefault('OPENAI_BASE_URL', 'http://localhost:11434/v1')
os.environ.setdefault('LLM_PROVIDER', 'openai')
os.environ.setdefault('REDIS_HOST', 'localhost')
os.environ.setdefault('REDIS_PORT', '6379')
os.environ.setdefault('TTS_SERVICE_URL', 'http://localhost:4123/v1/audio/speech')

# Add server directory to path for app imports
server_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'server'))
sys.path.insert(0, server_path)


@pytest.fixture
def test_pdf_path():
    """Path to the test PDF document."""
    return os.path.join(os.path.dirname(__file__), '..', '2507.08034v1.pdf')


@pytest.fixture
def test_pdf_content(test_pdf_path):
    """Load test PDF content as bytes."""
    if os.path.exists(test_pdf_path):
        with open(test_pdf_path, 'rb') as f:
            return f.read()
    else:
        # Return dummy content if file doesn't exist
        return b"Sample PDF content for testing"


@pytest.fixture
def mock_redis_service():
    """Mock Redis service with common operations."""
    mock = AsyncMock()
    
    # Job status storage
    job_storage = {}
    
    async def mock_set_job_status(job_id: str, status: str, message: str = "", progress: int = 0, metadata: Dict = None):
        job_storage[job_id] = {
            "job_id": job_id,
            "status": status,
            "message": message,
            "progress": progress,
            "updated_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
    
    async def mock_get_job_status(job_id: str):
        return job_storage.get(job_id)
    
    async def mock_update_job_progress(job_id: str, progress: int, message: str = ""):
        if job_id in job_storage:
            job_storage[job_id]["progress"] = progress
            job_storage[job_id]["message"] = message
            job_storage[job_id]["updated_at"] = datetime.now().isoformat()
    
    mock.set_job_status = mock_set_job_status
    mock.get_job_status = mock_get_job_status
    mock.update_job_progress = mock_update_job_progress
    mock.health_check = AsyncMock(return_value=True)
    
    return mock


@pytest.fixture
def mock_llm_service():
    """Mock LLM service that generates script scenes."""
    async def mock_generate_script(file_context):
        """Generate mock script with 5 scenes."""
        await asyncio.sleep(0.1)  # Simulate processing time
        
        return [
            {
                "id": 1,
                "narration_text": "Welcome to this lecture on advanced machine learning concepts.",
                "visual_type": "slide",
                "visual_prompt": "Create a title slide with 'Machine Learning' as the main heading"
            },
            {
                "id": 2,
                "narration_text": "Let's explore the fundamental concepts of neural networks.",
                "visual_type": "diagram",
                "visual_prompt": "Create a diagram showing neural network architecture"
            },
            {
                "id": 3,
                "narration_text": "The performance metrics show significant improvements over baseline.",
                "visual_type": "chart",
                "visual_prompt": "Create a bar chart comparing model performance"
            },
            {
                "id": 4,
                "narration_text": "Here's the implementation in Python using TensorFlow.",
                "visual_type": "code",
                "visual_prompt": "Show Python code for neural network implementation"
            },
            {
                "id": 5,
                "narration_text": "In conclusion, these techniques provide robust solutions.",
                "visual_type": "slide",
                "visual_prompt": "Create a conclusion slide summarizing key points"
            }
        ]
    
    mock = AsyncMock()
    mock.generate_script = mock_generate_script
    mock.check_health = AsyncMock(return_value=True)
    
    return mock


@pytest.fixture
def mock_tts_service():
    """Mock TTS service that generates audio."""
    async def mock_generate_audio(scene):
        """Generate mock audio data."""
        await asyncio.sleep(0.05)  # Simulate TTS processing
        
        job_id = scene.get("job_id", "test_job")
        scene_id = scene.get("id", 1)
        
        return {
            "path": f"/tmp/job_{job_id}_scene_{scene_id}_audio.mp3",
            "duration": 5.0,
            "status": "success",
            "size_bytes": 80000
        }
    
    mock = AsyncMock()
    mock.generate_audio = mock_generate_audio
    mock.check_health = AsyncMock(return_value=True)
    
    return mock


@pytest.fixture
def mock_visual_service():
    """Mock visual service that generates images."""
    async def mock_generate_visual(scene, job_id):
        """Generate mock visual asset."""
        await asyncio.sleep(0.08)  # Simulate visual generation
        
        scene_id = scene.get("id", 1)
        visual_type = scene.get("visual_type", "slide")
        
        return {
            "path": f"/tmp/job_{job_id}_scene_{scene_id}_{visual_type}.png",
            "status": "success",
            "visual_type": visual_type,
            "size_bytes": 150000
        }
    
    mock = AsyncMock()
    mock.generate_visual_asset = mock_generate_visual
    
    return mock


@pytest.fixture
def mock_job_service():
    """Mock job service for job management."""
    mock = MagicMock()
    
    job_data = {}
    
    async def mock_initialize_job(job_id: str, message: str = "", progress: int = 0):
        job_data[job_id] = {
            "status": "processing",
            "message": message,
            "progress": progress,
            "segments": {}
        }
    
    async def mock_get_job_status(job_id: str):
        return job_data.get(job_id)
    
    async def mock_update_job_progress(job_id: str, progress: int, message: str):
        if job_id in job_data:
            job_data[job_id]["progress"] = progress
            job_data[job_id]["message"] = message
    
    async def mock_is_cancelled(job_id: str):
        return False
    
    async def mock_set_job_status(job_id: str, status: str, message: str = "", progress: int = 100):
        if job_id in job_data:
            job_data[job_id]["status"] = status
            job_data[job_id]["message"] = message
            job_data[job_id]["progress"] = progress
    
    async def mock_update_segment(job_id: str, scene_id: int, segment_data: Dict):
        if job_id in job_data:
            job_data[job_id]["segments"][str(scene_id)] = segment_data
    
    mock.initialize_job = mock_initialize_job
    mock.get_job_status = mock_get_job_status
    mock.update_job_progress = mock_update_job_progress
    mock.is_job_cancelled = mock_is_cancelled
    mock.set_job_status = mock_set_job_status
    mock.update_segment = mock_update_segment
    
    return mock


@pytest.fixture
def reports_dir():
    """Ensure reports directory exists."""
    reports_path = os.path.join(os.path.dirname(__file__), 'reports')
    os.makedirs(reports_path, exist_ok=True)
    return reports_path


@pytest.fixture
def mock_file_context(test_pdf_content):
    """Create a mock file context object."""
    from unittest.mock import MagicMock
    
    mock_file = MagicMock()
    mock_file.filename = "2507.08034v1.pdf"
    mock_file.contents = test_pdf_content
    mock_file.content_type = "application/pdf"
    
    return mock_file


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
