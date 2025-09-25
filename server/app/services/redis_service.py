import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisService:
    """
    Service for managing job status and data in Redis.
    """

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None

    async def get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self.redis_client is None:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True  # Decode responses to strings
            )
        return self.redis_client

    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None

    async def health_check(self) -> bool:
        """
        Check if Redis connection is healthy.
        
        Returns:
            True if Redis is accessible, False otherwise
        """
        try:
            client = await self.get_client()
            # Simple ping to test connection
            await client.ping()
            return True
        except Exception as e:
            logger.error("Redis health check failed", extra={
                "error_type": type(e).__name__,
                "error": str(e)
            })
            # Reset client on failure to force reconnection
            self.redis_client = None
            return False
    # Job Status Management
    async def set_job_status(
        self,
        job_id: str,
        status: str,
        message: Optional[str] = None,
        progress: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Set job status with metadata.

        Args:
            job_id: Unique job identifier
            status: Job status (pending, processing, completed, failed)
            message: Optional status message
            progress: Optional progress percentage (0-100)
            metadata: Optional additional metadata
        """
        client = await self.get_client()

        job_data = {
            "job_id": job_id,
            "status": status,
            "updated_at": datetime.utcnow().isoformat(),
        }

        if message:
            job_data["message"] = message
        if progress is not None:
            job_data["progress"] = str(progress)
        if metadata:
            job_data.update(metadata)

        # Use pipeline for atomic operations
        async with client.pipeline() as pipe:
            pipe.hset(f"job:{job_id}", mapping=job_data)
            pipe.expire(f"job:{job_id}", 86400)  # 24 hours
            await pipe.execute()

        # Avoid using 'message' key in logger extra to prevent LogRecord overwrite
        logger.info(
            "Job status updated",
            extra={
                "job_id": job_id,
                "status": status,
                "job_message": message  # Renamed to avoid conflict
            }
        )

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job status and metadata.

        Args:
            job_id: Unique job identifier

        Returns:
            Job data dictionary or None if not found
        """
        client = await self.get_client()

        job_data = await client.hgetall(f"job:{job_id}")

        if not job_data:
            return None

        # Convert progress to int if present
        if "progress" in job_data and job_data["progress"]:
            try:
                job_data["progress"] = int(job_data["progress"])
            except (ValueError, TypeError):
                job_data["progress"] = None

        return job_data

    async def update_job_progress(self, job_id: str, progress: int, message: Optional[str] = None) -> None:
        """
        Update job progress percentage.

        Args:
            job_id: Unique job identifier
            progress: Progress percentage (0-100)
            message: Optional progress message
        """
        client = await self.get_client()

        updates = {
            "progress": str(progress),
            "updated_at": datetime.utcnow().isoformat()
        }

        if message:
            updates["message"] = message

        async with client.pipeline() as pipe:
            pipe.hset(f"job:{job_id}", mapping=updates)
            await pipe.execute()

        logger.debug("Job progress updated", extra={
            "job_id": job_id,
            "progress": progress,
            "message": message
        })

    async def set_job_result(self, job_id: str, result_data: Dict[str, Any]) -> None:
        """
        Set job result data.

        Args:
            job_id: Unique job identifier
            result_data: Result data to store
        """
        client = await self.get_client()

        # Store result as JSON string
        async with client.pipeline() as pipe:
            pipe.hset(f"job:{job_id}", "result", json.dumps(result_data))
            pipe.hset(f"job:{job_id}", "completed_at", datetime.utcnow().isoformat())
            await pipe.execute()

        logger.info("Job result stored", extra={"job_id": job_id})

    async def get_job_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job result data.

        Args:
            job_id: Unique job identifier

        Returns:
            Result data or None if not found
        """
        client = await self.get_client()

        result_json = await client.hget(f"job:{job_id}", "result")

        if not result_json:
            return None

        try:
            return json.loads(result_json)
        except json.JSONDecodeError:
            logger.error("Failed to decode job result", extra={"job_id": job_id})
            return None

    async def delete_job(self, job_id: str) -> bool:
        """
        Delete job data.

        Args:
            job_id: Unique job identifier

        Returns:
            True if job was deleted, False if not found
        """
        client = await self.get_client()

        deleted = await client.delete(f"job:{job_id}")

        if deleted:
            logger.info("Job deleted", extra={"job_id": job_id})

        return bool(deleted)

    async def list_jobs(self, pattern: str = "job:*", limit: int = 100) -> List[str]:
        """
        List job IDs matching pattern.

        Args:
            pattern: Redis key pattern
            limit: Maximum number of results

        Returns:
            List of job IDs
        """
        client = await self.get_client()

        keys = []
        async for key in client.scan_iter(match=pattern, count=limit):
            # Extract job ID from key (remove "job:" prefix)
            if key.startswith("job:"):
                keys.append(key[4:])

        return keys[:limit]


# Global Redis service instance
redis_service = RedisService()

async def check_redis_health() -> bool:
    """
    Global function to check Redis health for use in application health checks.
    
    Returns:
        True if Redis is healthy, False otherwise
    """
    return await redis_service.health_check()
