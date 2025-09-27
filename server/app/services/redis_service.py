import json
import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import redis.asyncio as redis
from functools import wraps
from app.core.config import settings
from enum import IntEnum

logger = logging.getLogger(__name__)


class JobPriority(IntEnum):
    """Job priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


def redis_retry(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator for Redis operations with exponential backoff retry.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except (redis.ConnectionError, redis.TimeoutError, redis.RedisError) as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(f"Redis operation {func.__name__} failed after {max_retries} retries",
                                   extra={"error": str(e), "attempts": attempt + 1})
                        raise e

                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Redis operation {func.__name__} failed, retrying in {delay}s",
                                 extra={"error": str(e), "attempt": attempt + 1, "delay": delay})
                    await asyncio.sleep(delay)
                except Exception as e:
                    # For non-Redis exceptions, don't retry
                    logger.error(f"Non-Redis error in {func.__name__}", extra={"error": str(e)})
                    raise e

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            raise Exception("Unexpected error in Redis retry logic")
        return wrapper
    return decorator


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
    # Job Status Management
    @redis_retry(max_retries=3, base_delay=1.0)
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

    @redis_retry(max_retries=2, base_delay=0.5)
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

    @redis_retry(max_retries=2, base_delay=0.5)
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

    @redis_retry(max_retries=2, base_delay=0.5)
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

    # Job Management Operations
    @redis_retry(max_retries=2, base_delay=0.5)
    async def cancel_job(self, job_id: str, reason: str = "User requested cancellation") -> bool:
        """
        Cancel a running job.

        Args:
            job_id: Unique job identifier
            reason: Reason for cancellation

        Returns:
            True if job was successfully cancelled, False otherwise
        """
        client = await self.get_client()

        try:
            # Check current job status
            job_data = await self.get_job_status(job_id)
            if not job_data:
                logger.warning("Attempted to cancel non-existent job", extra={"job_id": job_id})
                return False

            current_status = job_data.get("status", "")

            # Only allow cancellation for certain statuses
            cancellable_statuses = ["pending", "processing"]
            if current_status not in cancellable_statuses:
                logger.warning("Cannot cancel job in status", extra={
                    "job_id": job_id,
                    "status": current_status
                })
                return False

            # Set job status to cancelled
            await self.set_job_status(
                job_id=job_id,
                status="cancelled",
                message=f"Job cancelled: {reason}",
                progress=0
            )

            # Set cancellation timestamp
            async with client.pipeline() as pipe:
                pipe.hset(f"job:{job_id}", "cancelled_at", datetime.utcnow().isoformat())
                pipe.hset(f"job:{job_id}", "cancellation_reason", reason)
                await pipe.execute()

            logger.info("Job cancelled successfully", extra={
                "job_id": job_id,
                "reason": reason,
                "previous_status": current_status
            })

            return True

        except Exception as e:
            logger.error("Failed to cancel job", extra={
                "job_id": job_id,
                "error": str(e)
            })
            return False

    async def is_job_cancelled(self, job_id: str) -> bool:
        """
        Check if a job has been cancelled.

        Args:
            job_id: Unique job identifier

        Returns:
            True if job is cancelled, False otherwise
        """
        client = await self.get_client()

        try:
            status = await client.hget(f"job:{job_id}", "status")
            return status == "cancelled"
        except Exception as e:
            logger.error("Failed to check job cancellation status", extra={
                "job_id": job_id,
                "error": str(e)
            })
            return False

    async def get_job_cancellation_reason(self, job_id: str) -> Optional[str]:
        """
        Get the reason for job cancellation.

        Args:
            job_id: Unique job identifier

        Returns:
            Cancellation reason or None if not cancelled
        """
        client = await self.get_client()

        try:
            reason = await client.hget(f"job:{job_id}", "cancellation_reason")
            return reason
        except Exception as e:
            logger.error("Failed to get job cancellation reason", extra={
                "job_id": job_id,
                "error": str(e)
            })
            return None

    async def get_active_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get list of active (non-completed) jobs.

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of active job data
        """
        client = await self.get_client()

        try:
            # Get all job keys
            job_keys = []
            async for key in client.scan_iter(match="job:*", count=limit * 2):
                job_keys.append(key)

            active_jobs = []
            for key in job_keys[:limit]:
                job_data = await client.hgetall(key)
                status = job_data.get(b"status", b"").decode()

                # Only include non-terminal statuses
                if status not in ["completed", "completed_with_errors", "failed", "cancelled"]:
                    job_id = key[4:]  # Remove "job:" prefix
                    active_jobs.append({
                        "job_id": job_id,
                        "status": status,
                        "message": job_data.get(b"message", b"").decode(),
                        "progress": job_data.get(b"progress", b"").decode(),
                        "updated_at": job_data.get(b"updated_at", b"").decode()
                    })

            return active_jobs

        except Exception as e:
            logger.error("Failed to get active jobs", extra={"error": str(e)})
            return []

    # Priority Queue Operations
    @redis_retry(max_retries=2, base_delay=0.5)
    async def add_job_to_priority_queue(self, job_id: str, priority: JobPriority = JobPriority.NORMAL) -> bool:
        """
        Add a job to the priority queue.

        Args:
            job_id: Unique job identifier
            priority: Job priority level

        Returns:
            True if job was added to queue, False otherwise
        """
        client = await self.get_client()

        try:
            # Add to priority sorted set (higher priority = lower score for descending order)
            priority_score = priority.value * -1  # Negative for descending order

            # Use pipeline for atomic operations
            async with client.pipeline() as pipe:
                pipe.zadd("job_priority_queue", {job_id: priority_score})
                pipe.hset(f"job:{job_id}", "priority", priority.name)
                pipe.hset(f"job:{job_id}", "queued_at", datetime.utcnow().isoformat())
                await pipe.execute()

            logger.info("Job added to priority queue", extra={
                "job_id": job_id,
                "priority": priority.name,
                "priority_score": priority_score
            })

            return True

        except Exception as e:
            logger.error("Failed to add job to priority queue", extra={
                "job_id": job_id,
                "priority": priority.name,
                "error": str(e)
            })
            return False

    @redis_retry(max_retries=2, base_delay=0.5)
    async def get_next_priority_job(self) -> Optional[str]:
        """
        Get the next job from priority queue (highest priority first).

        Returns:
            Job ID or None if queue is empty
        """
        client = await self.get_client()

        try:
            # Get job with highest priority (lowest score)
            result = await client.zpopmin("job_priority_queue", count=1)

            if result:
                job_id = result[0][0]  # First element of first tuple
                logger.debug("Retrieved job from priority queue", extra={"job_id": job_id})
                return job_id

            return None

        except Exception as e:
            logger.error("Failed to get next priority job", extra={"error": str(e)})
            return None

    @redis_retry(max_retries=2, base_delay=0.5)
    async def update_job_priority(self, job_id: str, new_priority: JobPriority) -> bool:
        """
        Update job priority in queue.

        Args:
            job_id: Unique job identifier
            new_priority: New priority level

        Returns:
            True if priority was updated, False otherwise
        """
        client = await self.get_client()

        try:
            # Update priority score in sorted set
            priority_score = new_priority.value * -1

            # Check if job exists in queue
            current_score = await client.zscore("job_priority_queue", job_id)
            if current_score is None:
                # Job not in queue, add it
                return await self.add_job_to_priority_queue(job_id, new_priority)

            async with client.pipeline() as pipe:
                pipe.zadd("job_priority_queue", {job_id: priority_score})
                pipe.hset(f"job:{job_id}", "priority", new_priority.name)
                await pipe.execute()

            logger.info("Job priority updated", extra={
                "job_id": job_id,
                "old_priority": JobPriority(int(current_score) * -1).name,
                "new_priority": new_priority.name
            })

            return True

        except Exception as e:
            logger.error("Failed to update job priority", extra={
                "job_id": job_id,
                "new_priority": new_priority.name,
                "error": str(e)
            })
            return False

    @redis_retry(max_retries=2, base_delay=0.5)
    async def get_queue_length(self) -> int:
        """
        Get the number of jobs in priority queue.

        Returns:
            Number of jobs in queue
        """
        client = await self.get_client()

        try:
            length = await client.zcard("job_priority_queue")
            return length
        except Exception as e:
            logger.error("Failed to get queue length", extra={"error": str(e)})
            return 0

    @redis_retry(max_retries=2, base_delay=0.5)
    async def get_queue_status(self) -> Dict[str, Any]:
        """
        Get detailed queue status information.

        Returns:
            Dictionary with queue statistics
        """
        client = await self.get_client()

        try:
            # Get queue length
            queue_length = await self.get_queue_length()

            # Get priority distribution
            priority_counts = {}
            for priority in JobPriority:
                count = await client.zcount("job_priority_queue", priority.value * -1, priority.value * -1)
                priority_counts[priority.name] = count

            # Get oldest and newest jobs in queue
            oldest_jobs = await client.zrange("job_priority_queue", 0, 4, withscores=True)
            newest_jobs = await client.zrevrange("job_priority_queue", 0, 4, withscores=True)

            return {
                "queue_length": queue_length,
                "priority_distribution": priority_counts,
                "oldest_jobs": [{"job_id": job[0], "priority_score": job[1]} for job in oldest_jobs],
                "newest_jobs": [{"job_id": job[0], "priority_score": job[1]} for job in newest_jobs]
            }

        except Exception as e:
            logger.error("Failed to get queue status", extra={"error": str(e)})
            return {"error": str(e)}

    async def cleanup_expired_jobs(self, max_age_hours: int = 24) -> int:
        """
        Clean up jobs older than specified age.

        Args:
            max_age_hours: Maximum age in hours

        Returns:
            Number of jobs cleaned up
        """
        client = await self.get_client()

        try:
            cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)

            # Get all job keys
            job_keys = []
            async for key in client.scan_iter(match="job:*"):
                job_keys.append(key)

            cleaned_count = 0

            for key in job_keys:
                try:
                    # Get job update time
                    updated_at_str = await client.hget(key, "updated_at")
                    if updated_at_str:
                        updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00')).timestamp()

                        if updated_at < cutoff_time:
                            # Delete expired job
                            await client.delete(key)
                            cleaned_count += 1

                            logger.debug(f"Cleaned expired job: {key}")

                except Exception as e:
                    logger.error(f"Error processing job {key} for cleanup", extra={"error": str(e)})

            logger.info(f"Cleaned up {cleaned_count} expired jobs")
            return cleaned_count

        except Exception as e:
            logger.error("Failed to cleanup expired jobs", extra={"error": str(e)})
            return 0


# Global Redis service instance
redis_service = RedisService()
