import logging
from typing import Any, Dict

from app.services.job_service import job_service

logger = logging.getLogger(__name__)


class Composer:
    """Handle asset completion state using the in-memory job store."""

    async def handle_asset_completion(
        self, job_id: str, segment_id: int, asset_type: str, asset_data: Dict
    ) -> Dict[str, Any]:
        """Update asset data for a segment and persist it through the job store."""
        try:
            job_data = await job_service.get_job_status(job_id) or {}
            segments = job_data.setdefault("segments", {})
            segment_key = str(segment_id)
            current_segment = segments.get(
                segment_key,
                {"segment_id": segment_id, "audio_status": "pending", "visual_status": "pending"},
            )

            if asset_type == "audio":
                current_segment.update(
                    {
                        "audio_path": asset_data.get("path", ""),
                        "audio_duration": asset_data.get("duration", 0),
                        "audio_status": asset_data.get("status", "unknown"),
                    }
                )
            elif asset_type == "visual":
                current_segment.update(
                    {
                        "visual_path": asset_data.get("path", ""),
                        "visual_status": asset_data.get("status", "unknown"),
                        "visual_type": asset_data.get("visual_type", "unknown"),
                    }
                )

            segments[segment_key] = current_segment
            await job_service.set_job_status(
                job_id,
                status=job_data.get("status", "processing"),
                message=f"Updated segment {segment_id} {asset_type}",
                progress=job_data.get("progress"),
            )

            logger.info(
                "Asset completion handled",
                extra={
                    "job_id": job_id,
                    "segment_id": segment_id,
                    "asset_type": asset_type,
                    "asset_status": asset_data.get("status", "unknown"),
                },
            )

            return current_segment

        except Exception as exc:
            logger.error(
                "Failed to handle asset completion",
                extra={
                    "job_id": job_id,
                    "segment_id": segment_id,
                    "asset_type": asset_type,
                    "error": str(exc),
                },
            )
            raise

    async def get_job_status(self, job_id: str) -> Dict:
        """Return aggregated segment information for a job."""
        job_data = await job_service.get_job_status(job_id)
        if not job_data:
            return {"job_id": job_id, "segments": {}, "total_segments": 0}

        segments = job_data.get("segments", {})
        return {"job_id": job_id, "segments": segments, "total_segments": len(segments)}
