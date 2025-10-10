import asyncio
import json
import logging
import os
import threading
import time
from datetime import datetime
from enum import IntEnum
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class JobPriority(IntEnum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class JobStore:
    """Simple in-memory job store with optional file persistence."""

    def __init__(self) -> None:
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.queue: List[str] = []
        self._lock = asyncio.Lock()
        self._cleanup_thread: threading.Thread | None = None
        self._stop_cleanup = threading.Event()
        self._data_file = "/tmp/job_store.json"
        self._load_from_file()
        self._start_cleanup_thread()

    def _load_from_file(self) -> None:
        if not os.path.exists(self._data_file):
            return
        try:
            with open(self._data_file, encoding="utf-8") as handle:
                data = json.load(handle)
                self.jobs = data.get("jobs", {})
                self.queue = data.get("queue", [])
                logger.info("Loaded %d jobs from file", len(self.jobs))
        except Exception as exc:
            logger.warning("Failed to load job data from file: %s", exc)

    def _save_to_file(self) -> None:
        try:
            payload = {
                "jobs": self.jobs,
                "queue": self.queue,
                "timestamp": datetime.utcnow().isoformat(),
            }
            with open(self._data_file, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
        except Exception as exc:
            logger.error("Failed to save job data to file: %s", exc)

    def _start_cleanup_thread(self) -> None:
        def cleanup_worker() -> None:
            while not self._stop_cleanup.is_set():
                try:
                    self._cleanup_expired_jobs()
                except Exception as exc:
                    logger.error("Cleanup error: %s", exc)
                self._stop_cleanup.wait(300)

        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()

    def _cleanup_expired_jobs(self, max_age_hours: int = 24) -> int:
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)
        expired_jobs: List[str] = []

        for job_id, job_data in list(self.jobs.items()):
            updated_at_str = job_data.get("updated_at")
            if not updated_at_str:
                continue
            try:
                updated_at = datetime.fromisoformat(
                    updated_at_str.replace("Z", "+00:00")
                ).timestamp()
            except ValueError:
                expired_jobs.append(job_id)
                continue
            if updated_at < cutoff_time:
                expired_jobs.append(job_id)

        for job_id in expired_jobs:
            self._remove_job(job_id)
            logger.debug("Cleaned expired job: %s", job_id)

        if expired_jobs:
            logger.info("Cleaned up %d expired jobs", len(expired_jobs))
        return len(expired_jobs)

    def _remove_job(self, job_id: str) -> None:
        self.jobs.pop(job_id, None)
        if job_id in self.queue:
            self.queue.remove(job_id)

    async def save_job(
        self,
        job_id: str,
        status: str,
        message: str | None,
        progress: int | None,
        metadata: Dict[str, Any] | None = None,
    ) -> None:
        async with self._lock:
            payload = metadata.copy() if metadata else {}
            payload.update(
                {
                    "job_id": job_id,
                    "status": status,
                    "message": message,
                    "progress": progress,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "segments": payload.get("segments", {}),
                }
            )
            self.jobs[job_id] = payload
            self._save_to_file()

    async def update_job_status(
        self, job_id: str, status: str, message: str | None, progress: int | None
    ) -> None:
        async with self._lock:
            job = self.jobs.setdefault(job_id, {"job_id": job_id, "segments": {}})
            job["status"] = status
            if message is not None:
                job["message"] = message
            if progress is not None:
                job["progress"] = progress
            job["updated_at"] = datetime.utcnow().isoformat()
            self._save_to_file()

    async def update_job_metadata(self, job_id: str, **metadata: Any) -> None:
        async with self._lock:
            job = self.jobs.setdefault(job_id, {"job_id": job_id, "segments": {}})
            job.update(metadata)
            job["updated_at"] = datetime.utcnow().isoformat()
            self._save_to_file()

    async def update_segment(self, job_id: str, segment_id: int, data: Dict[str, Any]) -> None:
        async with self._lock:
            job = self.jobs.setdefault(job_id, {"job_id": job_id, "segments": {}})
            segments = job.setdefault("segments", {})
            segment_entry = segments.setdefault(str(segment_id), {"segment_id": segment_id})
            segment_entry.update(data)
            job["updated_at"] = datetime.utcnow().isoformat()
            self._save_to_file()

    async def cancel_job(self, job_id: str, reason: str) -> bool:
        async with self._lock:
            if job_id not in self.jobs:
                return False
            self.jobs[job_id].update(
                {
                    "status": "cancelled",
                    "cancellation_reason": reason,
                    "cancelled_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
            self._save_to_file()
            return True

    async def get_job(self, job_id: str) -> Dict[str, Any] | None:
        return self.jobs.get(job_id)

    async def get_job_result(self, job_id: str) -> Dict[str, Any] | None:
        job = self.jobs.get(job_id)
        return job.get("result") if job else None

    async def set_job_result(self, job_id: str, result: Dict[str, Any]) -> None:
        async with self._lock:
            job = self.jobs.setdefault(job_id, {"job_id": job_id, "segments": {}})
            job.update(
                {
                    "result": result,
                    "completed_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
            self._save_to_file()

    async def list_jobs(self, limit: int) -> List[str]:
        return list(self.jobs.keys())[:limit]

    async def get_active_jobs(self, limit: int) -> List[Dict[str, Any]]:
        active: List[Dict[str, Any]] = []
        for job_id, job in self.jobs.items():
            status = job.get("status", "")
            if status in {"completed", "completed_with_errors", "failed", "cancelled"}:
                continue
            active.append(
                {
                    "job_id": job_id,
                    "status": status,
                    "message": job.get("message"),
                    "progress": job.get("progress"),
                    "updated_at": job.get("updated_at"),
                }
            )
        return active[:limit]

    async def add_to_queue(self, job_id: str) -> None:
        async with self._lock:
            if job_id not in self.queue:
                self.queue.append(job_id)
                self._save_to_file()

    async def get_next_job(self) -> str | None:
        async with self._lock:
            if not self.queue:
                return None
            job_id = self.queue.pop(0)
            self._save_to_file()
            return job_id

    async def get_queue_length(self) -> int:
        return len(self.queue)

    def close(self) -> None:
        if self._cleanup_thread:
            self._stop_cleanup.set()
            self._cleanup_thread.join(timeout=5)
        self._save_to_file()

    def run_cleanup(self, max_age_hours: int = 24) -> Dict[str, Any]:
        before = len(self.jobs)
        cleaned = self._cleanup_expired_jobs(max_age_hours)
        after = len(self.jobs)
        return {
            "expired_jobs_cleaned": cleaned,
            "jobs_remaining": after,
            "jobs_removed": before - after,
            "queue_length": len(self.queue),
            "timestamp": datetime.utcnow().isoformat(),
        }


job_store = JobStore()


class JobService:
    """High-level utilities built on top of the JobStore."""

    def __init__(self, store: JobStore) -> None:
        self.store = store

    async def initialize_job(
        self, job_id: str, message: str | None = None, progress: int | None = None, **metadata: Any
    ) -> None:
        await self.store.save_job(
            job_id, status="pending", message=message, progress=progress, metadata=metadata
        )

    async def set_job_status(
        self, job_id: str, status: str, message: str | None = None, progress: int | None = None
    ) -> None:
        await self.store.update_job_status(job_id, status, message, progress)

    async def get_job_status(self, job_id: str) -> Dict[str, Any] | None:
        return await self.store.get_job(job_id)

    async def update_job_progress(
        self, job_id: str, progress: int, message: str | None = None
    ) -> None:
        await self.store.update_job_status(job_id, "processing", message, progress)

    async def update_job_metadata(self, job_id: str, **metadata: Any) -> None:
        await self.store.update_job_metadata(job_id, **metadata)

    async def update_segment(self, job_id: str, segment_id: int, data: Dict[str, Any]) -> None:
        await self.store.update_segment(job_id, segment_id, data)

    async def cancel_job(self, job_id: str, reason: str = "User requested cancellation") -> bool:
        return await self.store.cancel_job(job_id, reason)

    async def is_job_cancelled(self, job_id: str) -> bool:
        job = await self.store.get_job(job_id)
        return bool(job and job.get("status") == "cancelled")

    async def set_job_result(self, job_id: str, result_data: Dict[str, Any]) -> None:
        await self.store.set_job_result(job_id, result_data)

    async def get_job_result(self, job_id: str) -> Dict[str, Any] | None:
        return await self.store.get_job_result(job_id)

    async def list_jobs(self, limit: int = 100) -> List[str]:
        return await self.store.list_jobs(limit)

    async def get_active_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        return await self.store.get_active_jobs(limit)

    async def add_to_queue(self, job_id: str) -> None:
        await self.store.add_to_queue(job_id)

    async def get_next_job(self) -> str | None:
        return await self.store.get_next_job()

    async def get_queue_length(self) -> int:
        return await self.store.get_queue_length()

    def run_cleanup(self, max_age_hours: int = 24) -> Dict[str, Any]:
        return self.store.run_cleanup(max_age_hours)

    def shutdown(self) -> None:
        self.store.close()


job_service = JobService(job_store)
