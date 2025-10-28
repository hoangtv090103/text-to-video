"""
Test helper utilities for data handling and mock generation.
"""
import os
import asyncio
import random
from typing import Dict, Any, List


class MockDelaySimulator:
    """Simulate realistic service delays."""
    
    @staticmethod
    async def tts_delay(variance: float = 0.02):
        """Simulate TTS service delay (50ms ± variance)."""
        delay = 0.05 + random.uniform(-variance, variance)
        await asyncio.sleep(max(0.01, delay))
    
    @staticmethod
    async def llm_delay(variance: float = 0.05):
        """Simulate LLM service delay (100ms ± variance)."""
        delay = 0.1 + random.uniform(-variance, variance)
        await asyncio.sleep(max(0.02, delay))
    
    @staticmethod
    async def visual_delay(variance: float = 0.03):
        """Simulate visual service delay (80ms ± variance)."""
        delay = 0.08 + random.uniform(-variance, variance)
        await asyncio.sleep(max(0.02, delay))


class TestDataGenerator:
    """Generate test data for various scenarios."""
    
    @staticmethod
    def generate_mock_script(num_scenes: int = 5) -> List[Dict[str, Any]]:
        """Generate a mock script with specified number of scenes."""
        visual_types = ["slide", "diagram", "chart", "code", "formula"]
        scenes = []
        
        for i in range(1, num_scenes + 1):
            scene = {
                "id": i,
                "narration_text": f"This is scene {i} discussing important concepts in the lecture.",
                "visual_type": visual_types[(i - 1) % len(visual_types)],
                "visual_prompt": f"Create a {visual_types[(i - 1) % len(visual_types)]} for scene {i}"
            }
            scenes.append(scene)
        
        return scenes
    
    @staticmethod
    def generate_mock_audio_data(job_id: str, scene_id: int) -> Dict[str, Any]:
        """Generate mock audio asset data."""
        return {
            "path": f"/tmp/job_{job_id}_scene_{scene_id}_audio.mp3",
            "duration": random.uniform(4.0, 8.0),
            "status": "success",
            "size_bytes": random.randint(70000, 100000)
        }
    
    @staticmethod
    def generate_mock_visual_data(job_id: str, scene_id: int, visual_type: str) -> Dict[str, Any]:
        """Generate mock visual asset data."""
        return {
            "path": f"/tmp/job_{job_id}_scene_{scene_id}_{visual_type}.png",
            "status": "success",
            "visual_type": visual_type,
            "size_bytes": random.randint(100000, 200000)
        }


class MockServiceFailureSimulator:
    """Simulate various service failure scenarios."""
    
    def __init__(self, failure_rate: float = 0.0):
        """
        Initialize failure simulator.
        
        Args:
            failure_rate: Probability of failure (0.0 to 1.0)
        """
        self.failure_rate = failure_rate
        self.failure_count = 0
        self.call_count = 0
    
    def should_fail(self) -> bool:
        """Determine if this call should fail."""
        self.call_count += 1
        if random.random() < self.failure_rate:
            self.failure_count += 1
            return True
        return False
    
    def get_failure_rate(self) -> float:
        """Calculate actual failure rate."""
        if self.call_count == 0:
            return 0.0
        return self.failure_count / self.call_count


class ResourceMetricsCollector:
    """Collect resource usage metrics during tests."""
    
    def __init__(self):
        self.memory_samples = []
        self.cpu_samples = []
        self.start_time = None
        self.end_time = None
    
    def start(self):
        """Start collecting metrics."""
        import time
        self.start_time = time.time()
    
    def stop(self):
        """Stop collecting metrics."""
        import time
        self.end_time = time.time()
    
    def record_memory(self, memory_mb: float):
        """Record memory usage sample."""
        self.memory_samples.append(memory_mb)
    
    def record_cpu(self, cpu_percent: float):
        """Record CPU usage sample."""
        self.cpu_samples.append(cpu_percent)
    
    def get_duration(self) -> float:
        """Get total duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    def get_memory_stats(self) -> Dict[str, float]:
        """Get memory usage statistics."""
        if not self.memory_samples:
            return {"min": 0, "max": 0, "avg": 0, "peak": 0}
        
        return {
            "min": min(self.memory_samples),
            "max": max(self.memory_samples),
            "avg": sum(self.memory_samples) / len(self.memory_samples),
            "peak": max(self.memory_samples)
        }
    
    def get_cpu_stats(self) -> Dict[str, float]:
        """Get CPU usage statistics."""
        if not self.cpu_samples:
            return {"min": 0, "max": 0, "avg": 0, "peak": 0}
        
        return {
            "min": min(self.cpu_samples),
            "max": max(self.cpu_samples),
            "avg": sum(self.cpu_samples) / len(self.cpu_samples),
            "peak": max(self.cpu_samples)
        }


def load_test_pdf(pdf_path: str = None) -> bytes:
    """
    Load the test PDF file.
    
    Args:
        pdf_path: Path to PDF file. If None, uses default test PDF.
    
    Returns:
        PDF content as bytes
    """
    if pdf_path is None:
        # Default to the test PDF in parent directory
        pdf_path = os.path.join(os.path.dirname(__file__), '..', '2507.08034v1.pdf')
    
    if os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as f:
            return f.read()
    else:
        # Return dummy content for testing
        return b"%PDF-1.4\nDummy PDF content for testing"


def calculate_percentile(data: List[float], percentile: float) -> float:
    """
    Calculate percentile value from a list of numbers.
    
    Args:
        data: List of numeric values
        percentile: Percentile to calculate (0-100)
    
    Returns:
        Percentile value
    """
    if not data:
        return 0.0
    
    sorted_data = sorted(data)
    index = int((percentile / 100) * len(sorted_data))
    
    if index >= len(sorted_data):
        return sorted_data[-1]
    
    return sorted_data[index]
