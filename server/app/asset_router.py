import asyncio
import logging
import os
from collections.abc import Callable
from functools import wraps
from typing import Any, Dict

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

from app.services.visual_services import (
    call_presenton_api,
    generate_graph,
    render_code,
    render_diagram,
    render_formula,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


def exponential_backoff_retry(max_retries: int = 3, base_delay: float = 2.0):
    """
    Decorator to retry functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds, doubles each retry (default: 2.0)

    The delay sequence: 2s, 4s, 8s (for base_delay=2.0)
    Total max wait time: 14s across 3 retries
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_msg = str(e) if str(e) else type(e).__name__

                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(
                            f"Function {func.__name__} failed, retrying in {delay}s",
                            extra={
                                "error": error_msg,
                                "error_type": type(e).__name__,
                                "attempt": attempt + 1,
                                "delay": delay
                            }
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} retries",
                            extra={
                                "error": error_msg,
                                "error_type": type(e).__name__,
                                "attempts": attempt + 1
                            }
                        )
            raise last_exception
        return wrapper
    return decorator


@exponential_backoff_retry(max_retries=3, base_delay=1.0)
async def _call_visual_service(
    service_func: Callable, visual_prompt: str, job_id: str, scene_id: int
) -> str:
    """Wrapper function to apply retry logic to visual service calls."""
    return await service_func(visual_prompt, job_id, scene_id)


async def generate_visual_asset(scene: Dict, job_id: str = "unknown") -> Dict:
    """
    Route visual generation requests to the appropriate service based on visual_type.

    Args:
        job_id: Job identifier for logging
        scene: Scene dictionary containing visual_type, visual_prompt, and id

    Returns:
        Dictionary with visual asset information (path, status, scene_id)
    """
    scene_id: str = scene.get("id", "unknown")
    visual_type = scene.get("visual_type", "")
    visual_prompt = scene.get("visual_prompt", "")

    logger.info(
        "Starting visual asset generation",
        extra={
            "scene_id": scene_id,
            "visual_type": visual_type,
            "prompt_length": len(visual_prompt),
        },
    )

    try:
        # Create an output directory if it doesn't exist
        import os
        os.makedirs(settings.VISUAL_STORAGE_PATH, exist_ok=True)

        # Route to the appropriate visual service based on type
        # Harmonized to match LLM output: slide, diagram, chart, formula, code
        if visual_type in {"slide", "image"}:
            visual_path = await _call_visual_service(
                call_presenton_api, visual_prompt, job_id, scene_id
            )
        elif visual_type == "diagram":
            visual_path = await _call_visual_service(
                render_diagram, visual_prompt, job_id, scene_id
            )
        elif visual_type in {"graph", "chart"}:
            visual_path = await _call_visual_service(
                generate_graph, visual_prompt, job_id, scene_id
            )
        elif visual_type == "formula":
            visual_path = await _call_visual_service(
                render_formula, visual_prompt, job_id, scene_id
            )
        elif visual_type == "code":
            visual_path = await _call_visual_service(render_code, visual_prompt, job_id, scene_id)
        else:
            # Handle unsupported types with slide as default
            logger.warning(
                "Unsupported visual type, defaulting to slide",
                extra={"scene_id": scene_id, "visual_type": visual_type},
            )
            visual_path = await _call_visual_service(call_presenton_api, visual_prompt, job_id, scene_id)

        # Verify the file was actually created
        if not os.path.exists(visual_path):
            raise FileNotFoundError(f"Generated visual file not found: {visual_path}")

        # Get file size for logging
        file_size = os.path.getsize(visual_path)

        result = {
            "path": visual_path,
            "status": "success",
            "scene_id": scene_id,
            "visual_type": visual_type,
            "file_size": file_size,
            "timestamp": asyncio.get_event_loop().time(),
        }

        logger.info(
            "Visual asset generation completed",
            extra={
                "scene_id": scene_id,
                "visual_type": visual_type,
                "visual_path": visual_path,
                "file_size_bytes": file_size,
            },
        )

        return result

    except Exception as e:
        # Robust error handling - don't crash, return placeholder
        placeholder_path = await _create_error_placeholder(scene_id, visual_type, str(e))

        logger.error(
            "Visual asset generation failed, using placeholder",
            extra={
                "scene_id": scene_id,
                "visual_type": visual_type,
                "error": str(e),
                "placeholder_path": placeholder_path,
            },
        )

        return {
            "path": placeholder_path,
            "status": "failed_with_placeholder",
            "scene_id": scene_id,
            "visual_type": visual_type,
            "error": str(e),
            "timestamp": asyncio.get_event_loop().time(),
        }


async def _create_error_placeholder(scene_id: str, visual_type: str, error: str) -> str:
    """
    Create an error placeholder image when visual generation fails.

    Args:
        scene_id: Scene identifier
        visual_type: Type of visual that failed
        error: Error message

    Returns:
        Path to the created placeholder image
    """
    try:
        # Ensure output directory exists
        os.makedirs(settings.VISUAL_STORAGE_PATH, exist_ok=True)

        # Create error placeholder
        fig, ax = plt.subplots(figsize=(10, 6), facecolor="#ffebee")
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 6)
        ax.axis("off")

        # Add error content
        ax.text(
            5,
            4.5,
            f"[WARNING] Scene {scene_id}",
            fontsize=20,
            fontweight="bold",
            ha="center",
            va="center",
            color="#c62828",
        )
        ax.text(
            5,
            3.5,
            "Visual Generation Failed",
            fontsize=16,
            ha="center",
            va="center",
            color="#c62828",
        )
        ax.text(
            5, 2.8, f"Type: {visual_type}", fontsize=12, ha="center", va="center", color="#424242"
        )

        # Truncate error message if too long
        error_text = error[:60] + "..." if len(error) > 60 else error
        ax.text(
            5,
            2.2,
            f"Error: {error_text}",
            fontsize=10,
            ha="center",
            va="center",
            color="#424242",
            style="italic",
        )

        # Add error border
        border = mpatches.Rectangle(
            (0.5, 0.5), 9, 5, fill=False, edgecolor="#f44336", linewidth=3, linestyle="--"
        )
        ax.add_patch(border)

        placeholder_path = f"{settings.VISUAL_STORAGE_PATH}/error_scene_{scene_id}_{visual_type}.png"
        plt.tight_layout()
        plt.savefig(placeholder_path, dpi=150, bbox_inches="tight", facecolor="#ffebee")
        plt.close()

        return placeholder_path

    except Exception as create_error:
        # If even placeholder creation fails, return a simple path
        logger.error(
            "Failed to create error placeholder",
            extra={
                "scene_id": scene_id,
                "visual_type": visual_type,
                "placeholder_error": str(create_error),
            },
        )
        return f"{settings.VISUAL_STORAGE_PATH}/fallback_placeholder_scene_{scene_id}.png"
