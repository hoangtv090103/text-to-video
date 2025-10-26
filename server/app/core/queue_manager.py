import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class JobPriority(Enum):
    """Job priority levels"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class QueuedJob:
    """Represents a job in the queue"""

    job_id: str
    priority: JobPriority
    created_at: datetime
    file_size: int
    estimated_duration: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other):
        """Priority queue ordering (higher priority first, then FIFO)"""
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        return self.created_at < other.created_at


class JobQueue:
    """Priority-based job queue with resource management"""

    def __init__(self, max_queue_size: int = 100):
        self.max_queue_size = max_queue_size
        self._queue: List[QueuedJob] = []
        self._processing: Dict[str, QueuedJob] = {}
        self._completed: Dict[str, QueuedJob] = {}
        self._failed: Dict[str, QueuedJob] = {}

        self._queue_lock = asyncio.Lock()
        self._stats = {
            "total_submitted": 0,
            "total_completed": 0,
            "total_failed": 0,
            "average_wait_time": 0,
            "average_processing_time": 0,
        }

    async def submit_job(
        self,
        job_id: str,
        priority: JobPriority = JobPriority.NORMAL,
        file_size: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Submit a job to the queue"""
        async with self._queue_lock:
            if len(self._queue) >= self.max_queue_size:
                logger.warning(f"Queue full, rejecting job {job_id}")
                return False

            job = QueuedJob(
                job_id=job_id,
                priority=priority,
                created_at=datetime.now(timezone.utc),
                file_size=file_size,
                metadata=metadata or {},
            )

            # Insert job maintaining priority order
            inserted = False
            for i, existing_job in enumerate(self._queue):
                if job < existing_job:
                    self._queue.insert(i, job)
                    inserted = True
                    break

            if not inserted:
                self._queue.append(job)

            self._stats["total_submitted"] += 1

            logger.info(
                f"Job {job_id} submitted to queue",
                extra={
                    "job_id": job_id,
                    "priority": priority.name,
                    "queue_position": len(self._queue),
                    "file_size": file_size,
                },
            )

            return True

    async def get_next_job(self) -> Optional[QueuedJob]:
        """Get the next job from the queue"""
        async with self._queue_lock:
            if not self._queue:
                return None

            job = self._queue.pop(0)
            self._processing[job.job_id] = job

            wait_time = (datetime.now(timezone.utc) - job.created_at).total_seconds()
            logger.info(
                f"Job {job.job_id} started processing",
                extra={
                    "job_id": job.job_id,
                    "priority": job.priority.name,
                    "wait_time_seconds": wait_time,
                    "queue_size": len(self._queue),
                },
            )

            return job

    async def complete_job(self, job_id: str, processing_time: Optional[float] = None):
        """Mark a job as completed"""
        async with self._queue_lock:
            if job_id in self._processing:
                job = self._processing.pop(job_id)
                job.metadata["completed_at"] = datetime.now(timezone.utc)
                job.metadata["processing_time"] = processing_time

                self._completed[job_id] = job
                self._stats["total_completed"] += 1

                logger.info(f"Job {job_id} completed", extra={"job_id": job_id})

                # Update average processing time
                if processing_time:
                    current_avg = self._stats["average_processing_time"]
                    total_completed = self._stats["total_completed"]
                    self._stats["average_processing_time"] = (
                        current_avg * (total_completed - 1) + processing_time
                    ) / total_completed

    async def fail_job(self, job_id: str, error: str, retry: bool = True):
        """Mark a job as failed"""
        async with self._queue_lock:
            if job_id in self._processing:
                job = self._processing.pop(job_id)
                job.metadata["failed_at"] = datetime.now(timezone.utc)
                job.metadata["error"] = error

                if retry and job.retry_count < job.max_retries:
                    job.retry_count += 1
                    job.created_at = datetime.now(timezone.utc)  # Reset creation time for retry

                    # Re-insert into queue with same priority
                    inserted = False
                    for i, existing_job in enumerate(self._queue):
                        if job < existing_job:
                            self._queue.insert(i, job)
                            inserted = True
                            break

                    if not inserted:
                        self._queue.append(job)

                    logger.info(
                        f"Job {job_id} failed, retrying ({job.retry_count}/{job.max_retries})",
                        extra={"job_id": job_id, "error": error, "retry_count": job.retry_count},
                    )
                else:
                    self._failed[job_id] = job
                    self._stats["total_failed"] += 1

                    logger.error(
                        f"Job {job_id} failed permanently",
                        extra={"job_id": job_id, "error": error, "retry_count": job.retry_count},
                    )

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job from the queue"""
        async with self._queue_lock:
            # Remove from queue
            for i, job in enumerate(self._queue):
                if job.job_id == job_id:
                    self._queue.pop(i)
                    logger.info(f"Job {job_id} cancelled from queue")
                    return True

            # Check if currently processing
            if job_id in self._processing:
                job = self._processing.pop(job_id)
                job.metadata["cancelled_at"] = datetime.now(timezone.utc)
                self._failed[job_id] = job
                logger.info(f"Job {job_id} cancelled during processing")
                return True

            return False

    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        async with self._queue_lock:
            return {
                "queue_size": len(self._queue),
                "processing_count": len(self._processing),
                "completed_count": len(self._completed),
                "failed_count": len(self._failed),
                "stats": self._stats.copy(),
                "next_jobs": [
                    {
                        "job_id": job.job_id,
                        "priority": job.priority.name,
                        "created_at": job.created_at.isoformat(),
                        "file_size": job.file_size,
                        "retry_count": job.retry_count,
                    }
                    for job in self._queue[:5]  # Show next 5 jobs
                ],
                "processing_jobs": [
                    {
                        "job_id": job.job_id,
                        "priority": job.priority.name,
                        "created_at": job.created_at.isoformat(),
                        "retry_count": job.retry_count,
                    }
                    for job in self._processing.values()
                ],
            }

    async def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Clean up old completed/failed jobs"""
        async with self._queue_lock:
            cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)

            # Clean completed jobs
            old_completed = [
                job_id
                for job_id, job in self._completed.items()
                if job.created_at.timestamp() < cutoff_time
            ]
            for job_id in old_completed:
                del self._completed[job_id]

            # Clean failed jobs
            old_failed = [
                job_id
                for job_id, job in self._failed.items()
                if job.created_at.timestamp() < cutoff_time
            ]
            for job_id in old_failed:
                del self._failed[job_id]

            if old_completed or old_failed:
                logger.info(
                    f"Cleaned up {len(old_completed)} completed and {len(old_failed)} failed jobs"
                )


class QueueManager:
    """Manages job queues and processing"""

    def __init__(self):
        self.job_queue = JobQueue()
        self._processing_tasks: Dict[str, asyncio.Task] = {}
        self._shutdown_event = asyncio.Event()

    async def start_processing(self):
        """Start the queue processing loop"""
        logger.info("Starting job queue processing")

        while not self._shutdown_event.is_set():
            try:
                # Get next job
                job = await self.job_queue.get_next_job()
                if not job:
                    await asyncio.sleep(1)  # Wait for jobs
                    continue

                # Start processing job
                task = asyncio.create_task(self._process_job(job))
                self._processing_tasks[job.job_id] = task

                # Clean up completed tasks
                await self._cleanup_completed_tasks()

            except Exception as e:
                logger.error(f"Error in queue processing loop: {e}")
                await asyncio.sleep(5)

    async def _process_job(self, job: QueuedJob):
        """Process a single job"""
        start_time = time.time()

        try:
            logger.info(f"Processing job {job.job_id}")

            # Import here to avoid circular imports
            from app.orchestrator import create_video_job
            from app.utils.file import FileContext

            # Get file context from job metadata
            file_context = job.metadata.get("file_context")
            if not file_context:
                raise ValueError("No file context in job metadata")

            # Process the job
            await create_video_job(job.job_id, file_context)

            # Mark as completed
            processing_time = time.time() - start_time
            await self.job_queue.complete_job(job.job_id, processing_time)

        except Exception as e:
            logger.error(f"Job {job.job_id} processing failed: {e}")
            await self.job_queue.fail_job(job.job_id, str(e))

        finally:
            # Remove from processing tasks
            self._processing_tasks.pop(job.job_id, None)

    async def _cleanup_completed_tasks(self):
        """Clean up completed processing tasks"""
        completed_tasks = [job_id for job_id, task in self._processing_tasks.items() if task.done()]

        for job_id in completed_tasks:
            task = self._processing_tasks.pop(job_id)
            try:
                await task  # Get any exceptions
            except Exception as e:
                logger.error(f"Task for job {job_id} had exception: {e}")

    async def submit_job_for_processing(
        self,
        job_id: str,
        file_context,
        priority: JobPriority = JobPriority.NORMAL,
        file_size: int = 0,
    ) -> bool:
        """Submit a job for processing"""
        metadata = {"file_context": file_context}
        return await self.job_queue.submit_job(job_id, priority, file_size, metadata)

    async def cancel_job_processing(self, job_id: str) -> bool:
        """Cancel a job"""
        # Cancel the processing task if running
        if job_id in self._processing_tasks:
            task = self._processing_tasks[job_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self._processing_tasks[job_id]

        # Remove from queue
        return await self.job_queue.cancel_job(job_id)

    async def get_status(self) -> Dict[str, Any]:
        """Get queue manager status"""
        queue_status = await self.job_queue.get_queue_status()
        return {
            **queue_status,
            "processing_tasks": len(self._processing_tasks),
            "active_jobs": list(self._processing_tasks.keys()),
        }

    async def shutdown(self):
        """Shutdown the queue manager"""
        logger.info("Shutting down queue manager")

        # Signal shutdown
        self._shutdown_event.set()

        # Cancel all processing tasks
        for task in self._processing_tasks.values():
            task.cancel()

        # Wait for tasks to complete
        if self._processing_tasks:
            await asyncio.gather(*self._processing_tasks.values(), return_exceptions=True)

        # Cleanup old jobs
        await self.job_queue.cleanup_old_jobs()


# Global queue manager instance
queue_manager = QueueManager()
