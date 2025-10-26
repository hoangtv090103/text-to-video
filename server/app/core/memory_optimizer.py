import asyncio
import logging
import os
import tempfile
from typing import Dict, Optional, Any
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class MemoryOptimizer:
    """Optimizes memory usage for video generation tasks"""

    def __init__(self):
        self.temp_files: Dict[str, str] = {}
        self._cleanup_lock = asyncio.Lock()

    @asynccontextmanager
    async def temp_file_context(self, job_id: str, suffix: str = ".tmp"):
        """Context manager for temporary files with automatic cleanup"""
        temp_file = None
        try:
            # Create temporary file
            temp_fd, temp_path = tempfile.mkstemp(suffix=suffix)
            os.close(temp_fd)  # Close file descriptor, we'll use the path

            # Track for cleanup
            async with self._cleanup_lock:
                self.temp_files[temp_path] = job_id

            logger.debug(f"Created temp file: {temp_path} for job {job_id}")
            yield temp_path

        finally:
            # Cleanup temp file
            if temp_file and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                    async with self._cleanup_lock:
                        self.temp_files.pop(temp_path, None)
                    logger.debug(f"Cleaned up temp file: {temp_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {temp_path}: {e}")

    async def cleanup_job_files(self, job_id: str):
        """Clean up all temporary files for a specific job"""
        async with self._cleanup_lock:
            files_to_remove = [
                path for path, file_job_id in self.temp_files.items() if file_job_id == job_id
            ]

            for file_path in files_to_remove:
                try:
                    if os.path.exists(file_path):
                        os.unlink(file_path)
                        logger.debug(f"Cleaned up job file: {file_path}")
                    self.temp_files.pop(file_path, None)
                except Exception as e:
                    logger.warning(f"Failed to cleanup job file {file_path}: {e}")

    async def cleanup_all_files(self):
        """Clean up all tracked temporary files"""
        async with self._cleanup_lock:
            for file_path in list(self.temp_files.keys()):
                try:
                    if os.path.exists(file_path):
                        os.unlink(file_path)
                        logger.debug(f"Cleaned up temp file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {file_path}: {e}")
            self.temp_files.clear()

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get current memory usage statistics"""
        try:
            import psutil

            process = psutil.Process()
            memory_info = process.memory_info()

            return {
                "rss_mb": memory_info.rss / (1024 * 1024),  # Resident Set Size
                "vms_mb": memory_info.vms / (1024 * 1024),  # Virtual Memory Size
                "percent": process.memory_percent(),
                "temp_files_count": len(self.temp_files),
                "temp_files": list(self.temp_files.keys()),
            }
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"error": str(e)}


class StreamingFileHandler:
    """Handles streaming file operations to reduce memory usage"""

    @staticmethod
    async def stream_file_chunks(file_path: str, chunk_size: int = 8192):
        """Stream file in chunks to reduce memory usage"""
        try:
            async with aiofiles.open(file_path, "rb") as f:
                while True:
                    chunk = await f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        except Exception as e:
            logger.error(f"Failed to stream file {file_path}: {e}")
            raise

    @staticmethod
    async def copy_file_streaming(source: str, destination: str, chunk_size: int = 8192):
        """Copy file using streaming to reduce memory usage"""
        try:
            async with aiofiles.open(source, "rb") as src:
                async with aiofiles.open(destination, "wb") as dst:
                    while True:
                        chunk = await src.read(chunk_size)
                        if not chunk:
                            break
                        await dst.write(chunk)
        except Exception as e:
            logger.error(f"Failed to copy file from {source} to {destination}: {e}")
            raise


class CacheOptimizer:
    """Optimizes cache usage and cleanup"""

    def __init__(self):
        self.cache_stats = {"hits": 0, "misses": 0, "evictions": 0}

    async def clear_expired_cache(self):
        """Clear expired cache entries"""
        try:
            from app.utils.cache import redis_client

            if redis_client:
                # Get all cache keys
                keys = await redis_client.keys("cache:*")

                expired_count = 0
                for key in keys:
                    try:
                        ttl = await redis_client.ttl(key)
                        if ttl == -1:  # No expiration set
                            await redis_client.expire(key, 3600)  # Set 1 hour expiration
                            expired_count += 1
                        elif ttl == -2:  # Key doesn't exist
                            expired_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to check TTL for key {key}: {e}")

                logger.info(
                    f"Cache cleanup completed, processed {len(keys)} keys, {expired_count} expired"
                )
                self.cache_stats["evictions"] += expired_count

        except Exception as e:
            logger.error(f"Failed to clear expired cache: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache_stats.copy()


# Global instances
memory_optimizer = MemoryOptimizer()
streaming_handler = StreamingFileHandler()
cache_optimizer = CacheOptimizer()


# Cleanup function for application shutdown
async def cleanup_resources():
    """Clean up all resources on application shutdown"""
    logger.info("Starting resource cleanup")

    try:
        # Close TTS client pool
        from app.services.tts_service import close_tts_client

        await close_tts_client()

        # Cleanup temporary files
        await memory_optimizer.cleanup_all_files()

        # Clear cache
        await cache_optimizer.clear_expired_cache()

        logger.info("Resource cleanup completed")

    except Exception as e:
        logger.error(f"Error during resource cleanup: {e}")
