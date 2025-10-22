import logging
import os

import matplotlib

matplotlib.use("Agg")
from typing import Dict

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

# Asset storage configuration
ASSET_STORAGE_PATH = settings.VISUAL_STORAGE_PATH
os.makedirs(ASSET_STORAGE_PATH, exist_ok=True)


def generate_visual_asset_sync(scene: Dict, job_id: str) -> Dict:
    """
    Generate visual asset for a scene synchronously.

    Args:
        scene: Scene dictionary containing visual_type and visual_prompt
        job_id: Job identifier for file naming

    Returns:
        Dictionary with visual asset information
    """
    scene_id = scene.get("id", 1)
    visual_type = scene.get("visual_type", "slide")
    visual_prompt = scene.get("visual_prompt", "")

    logger.info(
        "Starting synchronous visual asset generation",
        extra={"scene_id": scene_id, "job_id": job_id, "visual_type": visual_type},
    )

    try:
        if visual_type == "slide":
            return _generate_slide_sync(visual_prompt, job_id, scene_id)
        if visual_type == "diagram":
            return _generate_diagram_sync(visual_prompt, job_id, scene_id)
        if visual_type == "animation":
            return _generate_animation_sync(visual_prompt, job_id, scene_id)
        if visual_type == "image":
            return _generate_image_sync(visual_prompt, job_id, scene_id)
        # Default to slide
        return _generate_slide_sync(visual_prompt, job_id, scene_id)

    except Exception as e:
        logger.error(
            "Visual asset generation failed",
            extra={
                "scene_id": scene_id,
                "job_id": job_id,
                "visual_type": visual_type,
                "error": str(e),
            },
        )

        return {"path": "", "status": "failed", "visual_type": visual_type, "error": str(e)}


def _generate_slide_sync(visual_prompt: str, job_id: str, scene_id: int) -> Dict:
    """
    Generate a slide synchronously using matplotlib fallback.
    """
    output_file = os.path.join(ASSET_STORAGE_PATH, f"job_{job_id}_scene_{scene_id}_slide.png")

    try:
        # Try Presenton API first
        presenton_result = _call_presenton_api_sync(visual_prompt, job_id, scene_id)
        if presenton_result and presenton_result.get("status") == "success":
            return presenton_result
    except Exception as e:
        logger.warning(
            "Presenton API failed, using matplotlib fallback",
            extra={"scene_id": scene_id, "error": str(e)},
        )

    # Fallback to matplotlib
    fig, ax = plt.subplots(figsize=(19.2, 10.8), facecolor="white", dpi=100)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis("off")

    # Simple background
    ax.add_patch(mpatches.Rectangle((0, 0), 16, 9, facecolor="#f8f9fa"))

    # Title
    title_text = f"Scene {scene_id}: Generated Slide"
    ax.text(
        8,
        7.5,
        title_text,
        fontsize=32,
        fontweight="bold",
        ha="center",
        va="center",
        color="#1a365d",
    )

    # Content
    content_lines = visual_prompt.split("\n")[:4]
    for i, line in enumerate(content_lines[:3]):
        y_pos = 6 - (i * 0.8)
        ax.text(8, y_pos, line[:80], fontsize=16, ha="center", va="center", color="#2d3748")

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()

    logger.info(
        "Slide generated successfully using matplotlib",
        extra={"scene_id": scene_id, "job_id": job_id, "output_file": output_file},
    )

    return {
        "path": output_file,
        "status": "success",
        "visual_type": "slide",
        "method": "matplotlib_fallback",
    }


def _generate_diagram_sync(visual_prompt: str, job_id: str, scene_id: int) -> Dict:
    """
    Generate a diagram synchronously using matplotlib.
    """
    output_file = os.path.join(ASSET_STORAGE_PATH, f"job_{job_id}_scene_{scene_id}_diagram.png")

    fig, ax = plt.subplots(figsize=(16, 9), facecolor="white", dpi=100)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    # Background
    ax.add_patch(mpatches.Rectangle((0, 0), 10, 6, facecolor="#ffffff"))

    # Title
    ax.text(
        5,
        5.5,
        f"Diagram: Scene {scene_id}",
        fontsize=24,
        fontweight="bold",
        ha="center",
        va="center",
        color="#2c3e50",
    )

    # Simple flowchart elements
    # Box 1
    ax.add_patch(mpatches.Rectangle((1, 3.5), 2, 1, facecolor="#3498db", alpha=0.7))
    ax.text(2, 4, "Input", fontsize=12, ha="center", va="center", color="white", fontweight="bold")

    # Arrow 1
    ax.arrow(3.2, 4, 1.3, 0, head_width=0.1, head_length=0.1, fc="#34495e", ec="#34495e")

    # Box 2
    ax.add_patch(mpatches.Rectangle((4.5, 3.5), 2, 1, facecolor="#e74c3c", alpha=0.7))
    ax.text(
        5.5, 4, "Process", fontsize=12, ha="center", va="center", color="white", fontweight="bold"
    )

    # Arrow 2
    ax.arrow(6.7, 4, 1.3, 0, head_width=0.1, head_length=0.1, fc="#34495e", ec="#34495e")

    # Box 3
    ax.add_patch(mpatches.Rectangle((8, 3.5), 1.5, 1, facecolor="#27ae60", alpha=0.7))
    ax.text(
        8.75, 4, "Output", fontsize=12, ha="center", va="center", color="white", fontweight="bold"
    )

    # Add description
    description_lines = visual_prompt.split("\n")[:2]
    for i, line in enumerate(description_lines):
        ax.text(5, 2.5 - i * 0.5, line[:60], fontsize=10, ha="center", va="center", color="#7f8c8d")

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()

    logger.info(
        "Diagram generated successfully",
        extra={"scene_id": scene_id, "job_id": job_id, "output_file": output_file},
    )

    return {"path": output_file, "status": "success", "visual_type": "diagram"}


def _generate_animation_sync(visual_prompt: str, job_id: str, scene_id: int) -> Dict:
    """
    Generate a static image representing animation synchronously.
    """
    output_file = os.path.join(ASSET_STORAGE_PATH, f"job_{job_id}_scene_{scene_id}_animation.png")

    fig, ax = plt.subplots(figsize=(16, 9), facecolor="white", dpi=100)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    # Background with motion effect
    ax.add_patch(mpatches.Rectangle((0, 0), 10, 6, facecolor="#ecf0f1"))

    # Title
    ax.text(
        5,
        5.5,
        f"Animation: Scene {scene_id}",
        fontsize=24,
        fontweight="bold",
        ha="center",
        va="center",
        color="#8e44ad",
    )

    # Create motion effect with circles
    for i in range(5):
        x = 2 + i * 1.5
        y = 3 + 0.5 * np.sin(i * 0.5)
        alpha = 1 - i * 0.15
        size = 500 - i * 80
        ax.scatter(x, y, s=size, alpha=alpha, c="#9b59b6")

    # Add description
    description_lines = visual_prompt.split("\n")[:2]
    for i, line in enumerate(description_lines):
        ax.text(5, 1.5 - i * 0.3, line[:60], fontsize=10, ha="center", va="center", color="#34495e")

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()

    logger.info(
        "Animation frame generated successfully",
        extra={"scene_id": scene_id, "job_id": job_id, "output_file": output_file},
    )

    return {"path": output_file, "status": "success", "visual_type": "animation"}


def _generate_image_sync(visual_prompt: str, job_id: str, scene_id: int) -> Dict:
    """
    Generate an image synchronously using matplotlib.
    """
    output_file = os.path.join(ASSET_STORAGE_PATH, f"job_{job_id}_scene_{scene_id}_image.png")

    fig, ax = plt.subplots(figsize=(16, 9), facecolor="white", dpi=100)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    # Background
    ax.add_patch(mpatches.Rectangle((0, 0), 10, 6, facecolor="#f39c12", alpha=0.2))

    # Title
    ax.text(
        5,
        5.5,
        f"Image: Scene {scene_id}",
        fontsize=24,
        fontweight="bold",
        ha="center",
        va="center",
        color="#d35400",
    )

    # Simple geometric art
    np.random.seed(scene_id)  # Reproducible random art
    for i in range(20):
        x = np.random.uniform(1, 9)
        y = np.random.uniform(1, 5)
        size = np.random.uniform(50, 200)
        color = np.random.choice(["#e74c3c", "#3498db", "#2ecc71", "#f39c12"])
        alpha = np.random.uniform(0.3, 0.8)
        ax.scatter(x, y, s=size, alpha=alpha, c=color)

    # Add description
    description_lines = visual_prompt.split("\n")[:2]
    for i, line in enumerate(description_lines):
        ax.text(
            5,
            0.8 - i * 0.3,
            line[:60],
            fontsize=10,
            ha="center",
            va="center",
            color="#2c3e50",
            bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "alpha": 0.8},
        )

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()

    logger.info(
        "Image generated successfully",
        extra={"scene_id": scene_id, "job_id": job_id, "output_file": output_file},
    )

    return {"path": output_file, "status": "success", "visual_type": "image"}


def _call_presenton_api_sync(visual_prompt: str, job_id: str, scene_id: int) -> Dict:
    """
    Call Presenton API synchronously to generate presentation slides.
    """
    logger.info(
        "Generating slide via Presenton API (sync)", extra={"scene_id": scene_id, "job_id": job_id}
    )

    try:
        # Get Presenton service URL from environment or use default
        presenton_url = os.environ.get("PRESENTON_URL", "http://localhost:5001")

        # Prepare request payload for Presenton API
        request_payload = {
            "content": visual_prompt,
            "n_slides": 1,  # Generate only one slide for this scene
            "language": "English",
            "template": "general",
            "export_as": "pdf",  # We'll convert the first slide to PNG
        }

        # Call Presenton generate presentation API
        response = requests.post(
            f"{presenton_url}/api/v1/ppt/presentation/generate",
            json=request_payload,
            headers={"Content-Type": "application/json"},
            # timeout=60,  # 60 second timeout
        )

        if response.status_code != 200:
            logger.error(
                "Presenton API failed",
                extra={
                    "scene_id": scene_id,
                    "job_id": job_id,
                    "status_code": response.status_code,
                    "response": response.text[:200],
                },
            )
            raise Exception(f"Presenton API returned {response.status_code}")

        # For now, create a placeholder since we'd need to implement PDF to PNG conversion
        # This would require additional libraries like pdf2image
        logger.info(
            "Presenton API call successful, using placeholder",
            extra={"scene_id": scene_id, "job_id": job_id},
        )

        # Return success to indicate API worked, but let fallback handle the actual file
        return {"path": "", "status": "api_success_needs_conversion", "visual_type": "slide"}

    except Exception as e:
        logger.error(
            "Presenton API call failed",
            extra={"scene_id": scene_id, "job_id": job_id, "error": str(e)},
        )
        raise e
