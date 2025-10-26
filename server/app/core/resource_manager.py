import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class ResourceLimits:
    """Resource limits configuration"""

    max_cpu_percent: float = 80.0
    max_memory_percent: float = 85.0
    max_concurrent_jobs: int = 3
    max_concurrent_tts: int = 2
    max_concurrent_visual: int = 4
    memory_cleanup_threshold: float = 70.0


class ResourceManager:
    """Manages system resources and concurrency limits"""

    def __init__(self, limits: Optional[ResourceLimits] = None):
        self.limits = limits or ResourceLimits()

        # Semaphores for different resource types
        self.job_semaphore = asyncio.Semaphore(self.limits.max_concurrent_jobs)
        self.tts_semaphore = asyncio.Semaphore(self.limits.max_concurrent_tts)
        self.visual_semaphore = asyncio.Semaphore(self.limits.max_concurrent_visual)

        # Resource monitoring
        self._last_cleanup = 0
        self._cleanup_interval = 30  # seconds

    async def check_system_resources(self) -> dict[str, float]:
        """Check current system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_available_gb": memory.available / (1024**3),
                "memory_used_gb": memory.used / (1024**3),
                "memory_total_gb": memory.total / (1024**3),
            }
        except Exception as e:
            logger.error(f"Failed to check system resources: {e}")
            return {"cpu_percent": 0, "memory_percent": 0}

    async def is_resource_available(self) -> bool:
        """Check if system has enough resources for new jobs"""
        resources = await self.check_system_resources()

        cpu_ok = resources["cpu_percent"] < self.limits.max_cpu_percent
        memory_ok = resources["memory_percent"] < self.limits.max_memory_percent

        if not cpu_ok or not memory_ok:
            logger.warning(
                "System resources exceeded",
                extra={
                    "cpu_percent": resources["cpu_percent"],
                    "memory_percent": resources["memory_percent"],
                    "cpu_limit": self.limits.max_cpu_percent,
                    "memory_limit": self.limits.max_memory_percent,
                },
            )
            return False

        return True

    async def cleanup_if_needed(self):
        """Trigger cleanup if memory usage is high"""
        import time

        current_time = time.time()

        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        resources = await self.check_system_resources()

        if resources["memory_percent"] > self.limits.memory_cleanup_threshold:
            logger.info(
                "Triggering memory cleanup",
                extra={
                    "memory_percent": resources["memory_percent"],
                    "threshold": self.limits.memory_cleanup_threshold,
                },
            )
            await self._force_cleanup()
            self._last_cleanup = current_time

    async def _force_cleanup(self):
        """Force garbage collection and cleanup"""
        import gc

        # Force garbage collection
        collected = gc.collect()
        logger.info(f"Garbage collection freed {collected} objects")

        # Clear any cached data if needed
        try:
            from app.utils.cache import clear_expired_cache

            await clear_expired_cache()
        except Exception as e:
            logger.warning(f"Cache cleanup failed: {e}")

    @asynccontextmanager
    async def acquire_job_slot(self, job_id: str):
        """Acquire a job processing slot"""
        logger.info(f"Requesting job slot for {job_id}")

        # Check system resources first
        if not await self.is_resource_available():
            raise Exception("System resources insufficient for new job")

        # Cleanup if needed
        await self.cleanup_if_needed()

        # Acquire semaphore
        await self.job_semaphore.acquire()
        try:
            logger.info(f"Acquired job slot for {job_id}")
            yield
        finally:
            self.job_semaphore.release()
            logger.info(f"Released job slot for {job_id}")

    @asynccontextmanager
    async def acquire_tts_slot(self, scene_id: str):
        """Acquire a TTS processing slot"""
        await self.tts_semaphore.acquire()
        try:
            logger.debug(f"Acquired TTS slot for scene {scene_id}")
            yield
        finally:
            self.tts_semaphore.release()
            logger.debug(f"Released TTS slot for scene {scene_id}")

    @asynccontextmanager
    async def acquire_visual_slot(self, scene_id: str):
        """Acquire a visual processing slot"""
        await self.visual_semaphore.acquire()
        try:
            logger.debug(f"Acquired visual slot for scene {scene_id}")
            yield
        finally:
            self.visual_semaphore.release()
            logger.debug(f"Released visual slot for scene {scene_id}")

    def get_status(self) -> dict:
        """Get current resource manager status"""
        return {
            "limits": {
                "max_concurrent_jobs": self.limits.max_concurrent_jobs,
                "max_concurrent_tts": self.limits.max_concurrent_tts,
                "max_concurrent_visual": self.limits.max_concurrent_visual,
                "max_cpu_percent": self.limits.max_cpu_percent,
                "max_memory_percent": self.limits.max_memory_percent,
            },
            "available_slots": {
                "jobs": self.job_semaphore._value,
                "tts": self.tts_semaphore._value,
                "visual": self.visual_semaphore._value,
            },
        }


# Global resource manager instance
resource_manager = ResourceManager()
