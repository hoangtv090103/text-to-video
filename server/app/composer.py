import asyncio
import logging
from typing import Dict
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class Composer:
    """
    Manages state and composition of audio/visual assets using Redis.
    """

    def __init__(self, redis_client: redis.Redis):
        """
        Initialize composer with Redis client.

        Args:
            redis_client: Async Redis client for state management
        """
        self.redis_client = redis_client

    async def handle_asset_completion(
        self,
        job_id: str,
        segment_id: int,
        asset_type: str,
        asset_data: Dict
    ) -> None:
        """
        Atomically handle completion of an asset (audio or visual) for a segment.

        Args:
            job_id: Unique identifier for the video generation job
            segment_id: Scene/segment identifier
            asset_type: Type of asset ('audio' or 'visual')
            asset_data: Asset metadata (path, duration, status, etc.)
        """
        segment_key = f"{job_id}:segment:{segment_id}"

        try:
            # Use Redis pipeline for atomic operations
            async with self.redis_client.pipeline() as pipe:
                # Watch the key for changes during transaction
                await pipe.watch(segment_key)

                # Start transaction
                pipe.multi()

                # Update segment state based on asset type
                if asset_type == "audio":
                    pipe.hset(segment_key, mapping={
                        "audio_path": asset_data.get("path", ""),
                        "audio_duration": str(asset_data.get("duration", 0)),
                        "audio_status": asset_data.get("status", "unknown")
                    })
                elif asset_type == "visual":
                    pipe.hset(segment_key, mapping={
                        "visual_path": asset_data.get("path", ""),
                        "visual_status": asset_data.get("status", "unknown"),
                        "visual_type": asset_data.get("visual_type", "unknown")
                    })

                # Set TTL for cleanup (24 hours)
                await pipe.expire(segment_key, 86400)

                # Execute transaction
                await pipe.execute()

            logger.info("Asset completion handled", extra={
                "job_id": job_id,
                "segment_id": segment_id,
                "asset_type": asset_type,
                "asset_status": asset_data.get("status", "unknown")
            })

            # Check if segment is complete after this update
            await self._check_segment_completion(job_id, segment_id)

        except redis.WatchError:
            logger.warning("Redis watch error, retrying asset completion", extra={
                "job_id": job_id,
                "segment_id": segment_id,
                "asset_type": asset_type
            })
            # Retry once on watch error
            await asyncio.sleep(0.1)
            await self.handle_asset_completion(job_id, segment_id, asset_type, asset_data)

        except Exception as e:
            logger.error("Failed to handle asset completion", extra={
                "job_id": job_id,
                "segment_id": segment_id,
                "asset_type": asset_type,
                "error": str(e)
            })
            raise

    async def _check_segment_completion(self, job_id: str, segment_id: int) -> None:
        """
        Check if a segment has both audio and visual assets ready.

        Args:
            job_id: Unique identifier for the video generation job
            segment_id: Scene/segment identifier
        """
        segment_key = f"{job_id}:segment:{segment_id}"

        try:
            # Get current segment state
            segment_state = await self.redis_client.hgetall(segment_key)

            # Check if both audio and visual assets are present
            has_audio = (
                segment_state.get(b"audio_path") and
                segment_state.get(b"audio_status") == b"success"
            )
            has_visual = (
                segment_state.get(b"visual_path") and
                segment_state.get(b"visual_status") in [b"success", b"failed_with_placeholder"]
            )

            if has_audio and has_visual:
                # Segment is ready for rendering
                await self.redis_client.hset(segment_key, "status", "ready_for_rendering")

                # Structured logging for segment completion
                logger.info("Segment ready for rendering", extra={
                    "job_id": job_id,
                    "segment_id": segment_id,
                    "audio_path": segment_state.get(b"audio_path", b"").decode(),
                    "visual_path": segment_state.get(b"visual_path", b"").decode(),
                    "audio_duration": segment_state.get(b"audio_duration", b"").decode(),
                    "visual_type": segment_state.get(b"visual_type", b"").decode(),
                    "status": "ready_for_rendering"
                })

                # In a full implementation, this would trigger video rendering
                # For prototype, logging is sufficient

        except Exception as e:
            logger.error("Failed to check segment completion", extra={
                "job_id": job_id,
                "segment_id": segment_id,
                "error": str(e)
            })

    async def get_job_status(self, job_id: str) -> Dict:
        """
        Get the current status of all segments for a job.

        Args:
            job_id: Unique identifier for the video generation job

        Returns:
            Dictionary with job status information
        """
        try:
            # Find all segment keys for this job
            segment_keys = await self.redis_client.keys(f"{job_id}:segment:*")

            segments_status = {}
            for key in segment_keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                segment_id = key_str.split(":")[-1]
                segment_data = await self.redis_client.hgetall(key)

                # Convert bytes to strings for JSON serialization
                segments_status[segment_id] = {
                    k.decode() if isinstance(k, bytes) else k:
                    v.decode() if isinstance(v, bytes) else v
                    for k, v in segment_data.items()
                }

            return {
                "job_id": job_id,
                "segments": segments_status,
                "total_segments": len(segments_status)
            }

        except Exception as e:
            logger.error("Failed to get job status", extra={
                "job_id": job_id,
                "error": str(e)
            })
            return {"job_id": job_id, "error": str(e)}
