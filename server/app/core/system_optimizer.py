import asyncio
import logging
import os
import sys
from typing import Dict, Any

# Add the server directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.resource_manager import resource_manager
from app.core.memory_optimizer import memory_optimizer, cleanup_resources
from app.core.queue_manager import queue_manager

logger = logging.getLogger(__name__)


class SystemOptimizer:
    """Main system optimizer that coordinates all optimization components"""

    def __init__(self):
        self.is_running = False
        self._monitoring_task: asyncio.Task = None

    async def start(self):
        """Start the system optimizer"""
        if self.is_running:
            logger.warning("System optimizer already running")
            return

        logger.info("Starting system optimizer")
        self.is_running = True

        # Start queue processing
        queue_task = asyncio.create_task(queue_manager.start_processing())

        # Start monitoring task
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

        try:
            # Wait for tasks
            await asyncio.gather(queue_task, self._monitoring_task)
        except Exception as e:
            logger.error(f"Error in system optimizer: {e}")
        finally:
            await self.stop()

    async def stop(self):
        """Stop the system optimizer"""
        if not self.is_running:
            return

        logger.info("Stopping system optimizer")
        self.is_running = False

        # Cancel monitoring task
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        # Shutdown queue manager
        await queue_manager.shutdown()

        # Cleanup resources
        await cleanup_resources()

        logger.info("System optimizer stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Check system resources
                resources = await resource_manager.check_system_resources()

                # Log resource usage
                logger.debug(
                    "System resource check",
                    extra={
                        "cpu_percent": resources.get("cpu_percent", 0),
                        "memory_percent": resources.get("memory_percent", 0),
                        "memory_available_gb": resources.get("memory_available_gb", 0),
                    },
                )

                # Trigger cleanup if needed
                await resource_manager.cleanup_if_needed()

                # Get queue status
                queue_status = await queue_manager.get_status()

                # Log queue status
                logger.debug(
                    "Queue status",
                    extra={
                        "queue_size": queue_status.get("queue_size", 0),
                        "processing_count": queue_status.get("processing_count", 0),
                        "completed_count": queue_status.get("completed_count", 0),
                        "failed_count": queue_status.get("failed_count", 0),
                    },
                )

                # Cleanup old jobs periodically
                await queue_manager.job_queue.cleanup_old_jobs()

                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            # Get resource status
            resources = await resource_manager.check_system_resources()
            resource_status = resource_manager.get_status()

            # Get queue status
            queue_status = await queue_manager.get_status()

            # Get memory stats
            memory_stats = memory_optimizer.get_memory_stats()

            # Get cache stats
            from app.core.memory_optimizer import cache_optimizer

            cache_stats = cache_optimizer.get_cache_stats()

            return {
                "system_resources": resources,
                "resource_limits": resource_status,
                "queue_status": queue_status,
                "memory_stats": memory_stats,
                "cache_stats": cache_stats,
                "optimizer_running": self.is_running,
            }

        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {"error": str(e)}


# Global system optimizer instance
system_optimizer = SystemOptimizer()


async def start_optimization():
    """Start the system optimization"""
    await system_optimizer.start()


async def stop_optimization():
    """Stop the system optimization"""
    await system_optimizer.stop()


async def get_optimization_status():
    """Get optimization status"""
    return await system_optimizer.get_system_status()
