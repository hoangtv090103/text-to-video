import asyncio
import logging
import aiofiles
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

# Asset storage configuration
ASSET_STORAGE_PATH = settings.VISUAL_STORAGE_PATH
os.makedirs(ASSET_STORAGE_PATH, exist_ok=True)


def sanitize_text_for_display(text: str) -> str:
    """
    Sanitize text to avoid LaTeX rendering issues with special characters and emojis.
    Replaces problematic characters with safe alternatives.
    """
    # Remove or replace emojis and special Unicode characters
    text = text.replace("💡", "[INFO]")
    text = text.replace("⚠️", "[WARNING]")
    text = text.replace("❌", "[ERROR]")
    text = text.replace("✅", "[OK]")
    # Escape LaTeX special characters
    latex_special_chars = {
        "#": "No.",
        "$": "\\$",
        "%": "\\%",
        "&": "\\&",
        "_": "\\_",
        "{": "\\{",
        "}": "\\}",
        "^": "\\^{}",
        "~": "\\~{}",
        "\\": "\\textbackslash{}",
    }
    for char, replacement in latex_special_chars.items():
        text = text.replace(char, replacement)
    return text


async def async_savefig(plt_instance, output_file: str, **kwargs):
    """Async wrapper for matplotlib savefig to avoid blocking."""
    import concurrent.futures
    import threading

    def _save():
        plt_instance.savefig(output_file, **kwargs)
        plt_instance.close()  # Clean up to save memory

    # Use thread pool to make savefig non-blocking
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        await loop.run_in_executor(executor, _save)


def _create_fallback_slide_matplotlib(visual_prompt: str, scene_id: int, output_file: str):
    """Create a professional-looking fallback slide with matplotlib when Presenton fails."""
    import matplotlib.pyplot as plt
    import numpy as np

    # Use higher DPI and better styling for fallback
    fig, ax = plt.subplots(figsize=(19.2, 10.8), facecolor="white", dpi=150)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis("off")

    # Professional gradient background
    gradient = np.linspace(0, 1, 256).reshape(1, -1)
    gradient = np.vstack([gradient] * 100)
    ax.imshow(gradient, extent=(0, 16, 0, 9), aspect="auto", cmap="Blues_r", alpha=0.08)

    # Parse visual_prompt for title and content
    lines = [line.strip() for line in visual_prompt.strip().split("\n") if line.strip()]
    title = lines[0] if lines else f"Scene {scene_id}"
    content_lines = lines[1:] if len(lines) > 1 else []

    # Main title with professional styling
    ax.text(
        8,
        7.8,
        title[:100],  # Increased from 80
        fontsize=36,  # Slightly smaller to fit more content
        fontweight="bold",
        ha="center",
        va="center",
        color="#1a365d",
        wrap=True,
    )

    # Content area with ALL bullet points (not limited to 5)
    y_position = 6.8
    line_height = 0.65
    max_lines = 10  # Show up to 10 lines instead of 5

    for line in content_lines[:max_lines]:
        if not line.strip() or y_position < 1.5:
            continue

        # Bullet point
        ax.plot([1.2], [y_position], marker="o", color="#4299e1", markersize=10)

        # Content text with increased length
        ax.text(
            1.7,
            y_position,
            line.strip()[:120],  # Increased from 90
            fontsize=18,  # Slightly smaller for more content
            ha="left",
            va="center",
            color="#2d3748",
            wrap=True,
        )
        y_position -= line_height

    # Professional accent bar
    accent_bar = mpatches.Rectangle((0.3, 1.5), 0.12, 6.8, facecolor="#4299e1", alpha=0.8, zorder=0)
    ax.add_patch(accent_bar)

    # Try to add decorative image/icon
    try:
        # Add small icon/image in top-right if possible
        keywords = " ".join(title.split()[:2])  # First 2 words for image search
        _try_add_slide_image(ax, keywords)
    except Exception:
        pass  # Continue without image

    # Bottom brand area
    brand_rect = mpatches.Rectangle((0, 0), 16, 1.2, facecolor="#1a365d", alpha=0.05)
    ax.add_patch(brand_rect)

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight", facecolor="white", edgecolor="none")
    plt.close()

    logger.warning(
        "📊 Created fallback slide with matplotlib (Presenton unavailable)",
        extra={"output_file": output_file, "lines_shown": min(len(content_lines), max_lines), "scene_id": scene_id},
    )


def _try_add_slide_image(ax, keywords: str):
    """Try to add image synchronously"""
    try:
        import urllib.request
        from PIL import Image as PILImage
        import io

        # Use Unsplash source (no API key needed)
        url = f"https://source.unsplash.com/300x200/?{keywords.replace(' ', ',')},professional"

        with urllib.request.urlopen(url) as response:
            if response.status == 200:
                img_data = response.read()
                img = PILImage.open(io.BytesIO(img_data))

                # Add image to top-right corner
                from matplotlib.offsetbox import OffsetImage, AnnotationBbox

                imagebox = OffsetImage(np.array(img), zoom=0.25)
                ab = AnnotationBbox(
                    imagebox,
                    (13.5, 7.5),
                    frameon=True,
                    box_alignment=(0.5, 0.5),
                    bboxprops={
                        "boxstyle": "round,pad=0.1",
                        "facecolor": "white",
                        "edgecolor": "#4299e1",
                        "linewidth": 2,
                    },
                )
                ax.add_artist(ab)
                logger.debug(f"Added image for keywords: {keywords}")
    except Exception as e:
        logger.debug(f"Could not add image: {e}")
        pass  # Silently fail


async def call_presenton_api(visual_prompt: str, job_id: str, scene_id: int) -> str:
    """
    Call Presenton API to generate high-quality presentation slides.

    Uses enhanced parameters for professional output:
    - tone: professional styling
    - verbosity: standard detail level
    - template: general (or custom if configured)
    - High-quality export settings
    """
    import httpx

    logger.info(
        "Generating slide via Presenton API", extra={"scene_id": scene_id, "job_id": job_id}
    )

    output_file = os.path.join(ASSET_STORAGE_PATH, f"job_{job_id}_scene_{scene_id}_slide.png")

    # Check cache first for visual assets
    from app.utils.cache import get_from_cache, set_cache

    cached_result = await get_from_cache("visual", visual_prompt)
    if cached_result and os.path.exists(cached_result):
        logger.info("Using cached visual asset", extra={"cached_path": cached_result})
        return cached_result

    # Check if Presenton service is available before trying to use it
    presenton_url = settings.PRESENTON_BASE_URL

    # Quick health check for Presenton service (check root endpoint)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            health_response = await client.get(f"{presenton_url}/")
            if health_response.status_code not in [200, 404]:  # 404 is OK if service is running
                logger.error(
                    "❌ Presenton service not healthy, using matplotlib fallback",
                    extra={"status_code": health_response.status_code, "url": presenton_url},
                )
                _create_fallback_slide_matplotlib(visual_prompt, scene_id, output_file)
                await set_cache("visual", visual_prompt, output_file)
                return output_file
            else:
                logger.info(
                    "✅ Presenton service is healthy and ready",
                    extra={"status_code": health_response.status_code, "url": presenton_url},
                )
    except Exception as health_error:
        logger.error(
            "❌ Presenton service not reachable, using matplotlib fallback",
            extra={"error": str(health_error), "url": presenton_url, "error_type": type(health_error).__name__},
        )
        _create_fallback_slide_matplotlib(visual_prompt, scene_id, output_file)
        await set_cache("visual", visual_prompt, output_file)
        return output_file

    try:
        # Get Presenton service URL from settings

        # Parse visual_prompt to extract key points and structure
        # Format: "Title: ...\nKey points:\n- point 1\n- point 2"
        instructions = """Create a professional, visually appealing slide with:
- Clear hierarchy and typography
- High contrast for readability
- Professional color scheme
- Balanced layout with whitespace
- Visual elements (icons, shapes) where appropriate"""

        # Simplified request payload to avoid Gemini schema depth issues
        # Presenton has issues with complex nested schemas
        request_payload = {
            "content": visual_prompt[:500],  # Limit content to avoid complexity
            "n_slides": 1,  # Generate only one slide
            "language": "English",
            "template": "general",
            "tone": "professional",
            "verbosity": "concise",  # Use concise to reduce schema complexity
            "include_title_slide": False,  # Simplify to reduce schema depth
            "include_table_of_contents": False,
            "web_search": False,
            "export_as": "pptx",  # PPTX instead of PDF (simpler conversion)
        }

        async with httpx.AsyncClient(timeout=90.0) as client:  # Increased timeout
            try:
                # Call Presenton generate presentation API
                response = await client.post(
                    f"{presenton_url}/api/v1/ppt/presentation/generate",
                    json=request_payload,
                    headers={"Content-Type": "application/json"},
                    # timeout=90.0,
                )

                if response.status_code != 200:
                    logger.error(
                        "❌ Presenton API generation failed, using matplotlib fallback",
                        extra={
                            "status_code": response.status_code,
                            "response": response.text[:300],
                            "error_hint": "Presenton may have internal LLM/schema issues",
                            "scene_id": scene_id,
                            "job_id": job_id,
                        },
                    )
                    _create_fallback_slide_matplotlib(visual_prompt, scene_id, output_file)
                    await set_cache("visual", visual_prompt, output_file)
                    return output_file

                result = response.json()
                presentation_path = result.get("path")

                if not presentation_path:
                    logger.error(
                        "❌ No presentation path returned from Presenton, using fallback",
                        extra={"scene_id": scene_id, "job_id": job_id, "response": result}
                    )
                    _create_fallback_slide_matplotlib(visual_prompt, scene_id, output_file)
                    await set_cache("visual", visual_prompt, output_file)
                    return output_file
                
                logger.info(
                    "✅ Presenton generated presentation successfully",
                    extra={"scene_id": scene_id, "job_id": job_id, "path": presentation_path}
                )

            except (httpx.TimeoutException, httpx.HTTPError) as e:
                logger.warning(
                    "Presenton connection error, using fallback",
                    extra={"error": str(e), "type": type(e).__name__}
                )
                _create_fallback_slide_matplotlib(visual_prompt, scene_id, output_file)
                await set_cache("visual", visual_prompt, output_file)
                return output_file

            # Download the generated presentation file
            # Save the PPTX temporarily with streaming download
            temp_pptx_path = os.path.join(ASSET_STORAGE_PATH, f"temp_{job_id}_{scene_id}.pptx")

            try:
                async with client.stream(
                    "GET", f"{presenton_url}{presentation_path}",
                    # timeout=60.0
                ) as download_response:
                    if download_response.status_code != 200:
                        logger.warning(
                            f"Failed to download presentation: {download_response.status_code}, using fallback"
                        )
                        _create_fallback_slide_matplotlib(visual_prompt, scene_id, output_file)
                        await set_cache("visual", visual_prompt, output_file)
                        return output_file

                    async with aiofiles.open(temp_pptx_path, "wb") as f:
                        async for chunk in download_response.aiter_bytes(chunk_size=8192):
                            await f.write(chunk)

            except Exception as download_error:
                logger.warning(
                    "Error downloading from Presenton, using fallback",
                    extra={"error": str(download_error)}
                )
                _create_fallback_slide_matplotlib(visual_prompt, scene_id, output_file)
                await set_cache("visual", visual_prompt, output_file)
                return output_file

            # Convert PPTX to PNG using LibreOffice/unoconv or fallback
            def convert_pptx_to_png():
                import subprocess

                try:
                    # Try using LibreOffice to convert PPTX to PNG
                    # LibreOffice headless mode for server environments
                    subprocess.run(
                        [
                            "soffice",
                            "--headless",
                            "--convert-to", "png",
                            "--outdir", ASSET_STORAGE_PATH,
                            temp_pptx_path
                        ],
                        check=True,
                        capture_output=True,
                        # timeout=30
                    )

                    # LibreOffice creates file with same name but .png extension
                    converted_file = temp_pptx_path.replace(".pptx", ".png")
                    if os.path.exists(converted_file):
                        # Rename to output_file
                        os.rename(converted_file, output_file)
                        # Clean up temp PPTX
                        os.remove(temp_pptx_path)
                        logger.info("Successfully converted PPTX to PNG")
                        return

                except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
                    logger.debug(f"LibreOffice conversion failed: {e}, trying ImageMagick")

                try:
                    # Fallback: Try ImageMagick for PPTX (if available)
                    subprocess.run(
                        [
                            "convert",
                            f"{temp_pptx_path}[0]",  # First slide
                            "-density", "300",
                            "-quality", "95",
                            "-background", "white",
                            "-alpha", "remove",
                            "-resize", "1920x1080^",
                            "-gravity", "center",
                            "-extent", "1920x1080",
                            output_file,
                        ],
                        check=True,
                        capture_output=True,
                        # timeout=30
                    )

                    # Clean up
                    os.remove(temp_pptx_path)
                    logger.info("Successfully converted PPTX to PNG via ImageMagick")
                    return

                except Exception as img_error:
                    logger.warning(f"ImageMagick conversion also failed: {img_error}")

                # Final fallback: create matplotlib slide
                logger.info("All PPTX conversion methods failed, using matplotlib fallback")
                create_fallback_slide()

            def create_fallback_slide():
                """Create a professional-looking fallback slide with high quality."""
                # Use higher DPI and better styling for fallback
                fig, ax = plt.subplots(figsize=(19.2, 10.8), facecolor="white", dpi=150)
                ax.set_xlim(0, 16)
                ax.set_ylim(0, 9)
                ax.axis("off")

                # Professional gradient background
                gradient = np.linspace(0, 1, 256).reshape(1, -1)
                gradient = np.vstack([gradient] * 100)
                ax.imshow(gradient, extent=(0, 16, 0, 9), aspect="auto", cmap="Blues_r", alpha=0.08)

                # Parse visual_prompt for title and content
                lines = [line.strip() for line in visual_prompt.strip().split("\n") if line.strip()]
                title = lines[0] if lines else f"Scene {scene_id}"
                content_lines = lines[1:] if len(lines) > 1 else []

                # Main title with professional styling
                ax.text(
                    8,
                    7.8,
                    title[:100],  # Increased from 80
                    fontsize=36,  # Slightly smaller to fit more content
                    fontweight="bold",
                    ha="center",
                    va="center",
                    color="#1a365d",
                    wrap=True,
                )

                # Content area with ALL bullet points (not limited to 5)
                y_position = 6.8
                line_height = 0.65
                max_lines = 10  # Show up to 10 lines instead of 5

                for i, line in enumerate(content_lines[:max_lines]):
                    if not line.strip() or y_position < 1.5:
                        continue

                    # Bullet point
                    ax.plot([1.2], [y_position], marker="o", color="#4299e1", markersize=10)

                    # Content text with increased length
                    ax.text(
                        1.7,
                        y_position,
                        line.strip()[:120],  # Increased from 90
                        fontsize=18,  # Slightly smaller for more content
                        ha="left",
                        va="center",
                        color="#2d3748",
                        wrap=True,
                    )
                    y_position -= line_height

                # Professional accent bar
                accent_bar = mpatches.Rectangle(
                    (0.3, 1.5), 0.12, 6.8, facecolor="#4299e1", alpha=0.8, zorder=0
                )
                ax.add_patch(accent_bar)

                # Bottom brand area
                brand_rect = mpatches.Rectangle((0, 0), 16, 1.2, facecolor="#1a365d", alpha=0.05)
                ax.add_patch(brand_rect)

                plt.tight_layout()
                # Save with high DPI
                plt.savefig(
                    output_file, dpi=150, bbox_inches="tight", facecolor="white", edgecolor="none"
                )
                plt.close()

            # Run conversion in executor to avoid blocking
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, convert_pptx_to_png)

            # Check if conversion succeeded
            if os.path.exists(output_file):
                logger.info(
                    "✅ Slide generated successfully via Presenton API",
                    extra={"scene_id": scene_id, "job_id": job_id, "output_file": output_file, "file_size": os.path.getsize(output_file)},
                )
                # Cache the successful result
                await set_cache("visual", visual_prompt, output_file)
            else:
                logger.error("❌ Presenton conversion failed, file not found, using matplotlib fallback")
                _create_fallback_slide_matplotlib(visual_prompt, scene_id, output_file)
                await set_cache("visual", visual_prompt, output_file)

    except Exception as e:
        # Log detailed error information
        import traceback

        error_details = {
            "scene_id": scene_id,
            "job_id": job_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()[:500],
        }
        logger.error(
            "Failed to generate slide via Presenton API, using fallback",
            extra=error_details,
        )

        # Fallback to COMPLETE slide generation with ALL content
        def create_fallback_slide():
            fig, ax = plt.subplots(figsize=(19.2, 10.8), facecolor="white", dpi=150)
            ax.set_xlim(0, 16)
            ax.set_ylim(0, 9)
            ax.axis("off")

            # Professional gradient background
            gradient = np.linspace(0, 1, 256).reshape(1, -1)
            gradient = np.vstack([gradient] * 100)
            ax.imshow(gradient, extent=(0, 16, 0, 9), aspect="auto", cmap="Blues_r", alpha=0.08)

            # Parse visual_prompt for title and content
            lines = [line.strip() for line in visual_prompt.strip().split("\n") if line.strip()]
            title = lines[0] if lines else f"Scene {scene_id}"
            content_lines = lines[1:] if len(lines) > 1 else []

            # Main title with professional styling
            ax.text(
                8,
                7.8,
                title[:100],
                fontsize=36,
                fontweight="bold",
                ha="center",
                va="center",
                color="#1a365d",
                wrap=True,
            )

            # Content area with ALL bullet points (not just 3-5)
            y_position = 6.8
            line_height = 0.65
            max_lines = 10  # Show up to 10 lines

            for i, line in enumerate(content_lines[:max_lines]):
                if not line.strip() or y_position < 1.5:
                    continue

                # Bullet point
                ax.plot([1.2], [y_position], marker="o", color="#4299e1", markersize=10)

                # Content text with word wrapping
                text_content = line.strip()[:120]  # Increased from 90
                ax.text(
                    1.7,
                    y_position,
                    text_content,
                    fontsize=18,  # Slightly smaller to fit more
                    ha="left",
                    va="center",
                    color="#2d3748",
                    wrap=True,
                )
                y_position -= line_height

            # Professional accent bar
            accent_bar = mpatches.Rectangle(
                (0.3, 1.5), 0.12, 6.8, facecolor="#4299e1", alpha=0.8, zorder=0
            )
            ax.add_patch(accent_bar)

            # Bottom brand area
            brand_rect = mpatches.Rectangle((0, 0), 16, 1.2, facecolor="#1a365d", alpha=0.05)
            ax.add_patch(brand_rect)

            plt.tight_layout()
            plt.savefig(
                output_file, dpi=150, bbox_inches="tight", facecolor="white", edgecolor="none"
            )
            plt.close()

        # Run fallback in executor
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, create_fallback_slide)

    # Cache the result (both success and fallback)
    from app.utils.cache import set_cache

    await set_cache("visual", visual_prompt, output_file)
    return output_file


async def render_diagram(visual_prompt: str, job_id: str, scene_id: int) -> str:
    """Renders a diagram using Mermaid service (mmdc CLI or online)."""
    output_file = os.path.join(ASSET_STORAGE_PATH, f"job_{job_id}_scene_{scene_id}_diagram.png")

    # Check cache first
    from app.utils.cache import get_from_cache, set_cache

    cached_result = await get_from_cache("visual", visual_prompt)
    if cached_result and os.path.exists(cached_result):
        logger.info("Using cached diagram", extra={"cached_path": cached_result, "scene_id": scene_id})
        return cached_result

    try:
        # Try to use Mermaid service (mmdc CLI preferred, then online)
        mermaid_result = await _render_with_mermaid(visual_prompt, output_file, job_id, scene_id)
        if mermaid_result and os.path.exists(mermaid_result):
            await set_cache("visual", visual_prompt, mermaid_result)
            return mermaid_result
    except Exception as e:
        logger.error(
            "❌ Mermaid rendering failed completely, using matplotlib fallback",
            extra={"scene_id": scene_id, "job_id": job_id, "error": str(e), "error_type": type(e).__name__},
        )

    # Fallback to matplotlib
    def create_diagram():
        fig, ax = plt.subplots(figsize=(12, 8), facecolor="white")
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 8)
        ax.axis("off")

        # Create simple flowchart
        boxes = [
            {"xy": (2, 6), "text": "Start"},
            {"xy": (5, 6), "text": "Process"},
            {"xy": (8, 6), "text": "End"},
        ]

        for i, box in enumerate(boxes):
            rect = mpatches.FancyBboxPatch(
                (box["xy"][0] - 0.8, box["xy"][1] - 0.4),
                1.6,
                0.8,
                boxstyle="round,pad=0.1",
                facecolor="lightblue",
                edgecolor="navy",
            )
            ax.add_patch(rect)
            ax.text(
                box["xy"][0],
                box["xy"][1],
                box["text"],
                ha="center",
                va="center",
                fontsize=12,
                fontweight="bold",
            )

            # Add arrows between boxes
            if i < len(boxes) - 1:
                ax.annotate(
                    "",
                    xy=(boxes[i + 1]["xy"][0] - 0.8, boxes[i + 1]["xy"][1]),
                    xytext=(box["xy"][0] + 0.8, box["xy"][1]),
                    arrowprops={"arrowstyle": "->", "lw": 2, "color": "navy"},
                )

        ax.text(
            5,
            1,
            f"Diagram for Scene {scene_id}",
            ha="center",
            va="center",
            fontsize=14,
            style="italic",
        )

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close()

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, create_diagram)

    logger.info(
        "📊 Created diagram with matplotlib fallback",
        extra={"scene_id": scene_id, "job_id": job_id, "output": output_file}
    )

    # Cache the result
    from app.utils.cache import set_cache

    await set_cache("visual", visual_prompt, output_file)
    return output_file


async def generate_graph(visual_prompt: str, job_id: str, scene_id: int) -> str:
    """
    Generates a professional chart/graph using matplotlib with enhanced features.
    Parses the visual_prompt to extract data, labels, and styling preferences.
    """
    output_file = os.path.join(ASSET_STORAGE_PATH, f"job_{job_id}_scene_{scene_id}_chart.png")

    # Check cache first
    from app.utils.cache import get_from_cache, set_cache

    cached_result = await get_from_cache("visual", visual_prompt)
    if cached_result and os.path.exists(cached_result):
        logger.info("Using cached visual asset", extra={"cached_path": cached_result})
        return cached_result

    def parse_chart_data(prompt: str):
        """Parse visual_prompt to extract chart data and configuration."""
        import re

        config = {
            "type": "bar",  # default
            "title": "Data Visualization",
            "xlabel": "Categories",
            "ylabel": "Values",
            "categories": [],
            "values": [],
            "colors": [
                "#2E86AB",
                "#A23B72",
                "#F18F01",
                "#C73E1D",
                "#6A994E",
            ],  # Professional palette
        }

        # Detect chart type
        if "line" in prompt.lower():
            config["type"] = "line"
        elif "pie" in prompt.lower():
            config["type"] = "pie"
        elif "scatter" in prompt.lower():
            config["type"] = "scatter"
        elif "area" in prompt.lower():
            config["type"] = "area"

        # Extract title
        title_match = re.search(r"[Tt]itle:\s*['\"]?([^'\"\\n]+)['\"]?", prompt)
        if title_match:
            config["title"] = title_match.group(1).strip()

        # Extract axis labels
        xlabel_match = re.search(r"[Xx]-axis:\s*['\"]?([^'\"\\n]+)['\"]?", prompt)
        if xlabel_match:
            config["xlabel"] = xlabel_match.group(1).strip()

        ylabel_match = re.search(r"[Yy]-axis:\s*['\"]?([^'\"\\n]+)['\"]?", prompt)
        if ylabel_match:
            config["ylabel"] = ylabel_match.group(1).strip()

        # Extract data points - look for patterns like "72%, 85%, 92%" or "23, 45, 56"
        data_match = re.search(r"[Dd]ata:\s*([0-9%,.\s]+)", prompt)
        if data_match:
            data_str = data_match.group(1)
            # Parse numbers (with or without %)
            values_raw = re.findall(r"(\d+\.?\d*)\%?", data_str)
            config["values"] = [float(v) for v in values_raw if v]

        # Extract categories - look for lists in parentheses or after keywords
        cat_match = re.search(r"(?:[Cc]ategories|[Ll]abels):\s*\(([^)]+)\)", prompt)
        if not cat_match:
            cat_match = re.search(r"(?:[Cc]ategories|[Ll]abels):\s*([A-Za-z0-9,\s]+)", prompt)

        if cat_match:
            cat_str = cat_match.group(1)
            config["categories"] = [c.strip() for c in cat_str.split(",")]

        # If no data found, use defaults
        if not config["values"]:
            config["values"] = [65, 78, 90, 72, 85]
        if not config["categories"]:
            config["categories"] = [f"Item {i + 1}" for i in range(len(config["values"]))]

        # Ensure categories and values have same length
        if len(config["categories"]) < len(config["values"]):
            config["categories"].extend(
                [f"Item {i + 1}" for i in range(len(config["categories"]), len(config["values"]))]
            )
        elif len(config["values"]) < len(config["categories"]):
            config["values"].extend([0] * (len(config["categories"]) - len(config["values"])))

        return config

    def create_chart():
        config = parse_chart_data(visual_prompt)

        # Use high-quality figure settings
        plt.style.use("seaborn-v0_8-darkgrid")
        fig, ax = plt.subplots(figsize=(14, 8), facecolor="white", dpi=150)

        chart_type = config["type"]
        categories = config["categories"]
        values = config["values"]
        colors = config["colors"]

        if chart_type == "bar":
            # Professional bar chart
            bars = ax.bar(
                categories,
                values,
                color=colors[: len(categories)],
                edgecolor="white",
                linewidth=1.5,
                alpha=0.9,
            )

            # Add value labels on top of bars
            for bar in bars:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"{height:.1f}",
                    ha="center",
                    va="bottom",
                    fontsize=11,
                    fontweight="bold",
                )

            ax.set_xlabel(config["xlabel"], fontsize=14, fontweight="bold")
            ax.set_ylabel(config["ylabel"], fontsize=14, fontweight="bold")
            ax.grid(axis="y", alpha=0.3, linestyle="--")

        elif chart_type == "line":
            # Professional line chart
            x_pos = range(len(values))
            ax.plot(
                x_pos,
                values,
                marker="o",
                linewidth=3,
                markersize=10,
                color=colors[0],
                markerfacecolor=colors[1],
                markeredgecolor="white",
                markeredgewidth=2,
            )

            # Add value labels
            for i, v in enumerate(values):
                ax.text(i, v, f"{v:.1f}", ha="center", va="bottom", fontsize=10, fontweight="bold")

            ax.set_xticks(x_pos)
            ax.set_xticklabels(categories)
            ax.set_xlabel(config["xlabel"], fontsize=14, fontweight="bold")
            ax.set_ylabel(config["ylabel"], fontsize=14, fontweight="bold")
            ax.grid(True, alpha=0.3, linestyle="--")

        elif chart_type == "pie":
            # Professional pie chart
            wedges, texts, autotexts = ax.pie(
                values,
                labels=categories,
                colors=colors[: len(categories)],
                autopct="%1.1f%%",
                startangle=90,
                pctdistance=0.85,
                explode=[0.05] * len(values),  # Slight separation
            )

            # Enhance text styling
            for text in texts:
                text.set_fontsize(12)
                text.set_fontweight("bold")
            for autotext in autotexts:
                autotext.set_color("white")
                autotext.set_fontsize(11)
                autotext.set_fontweight("bold")

        elif chart_type == "scatter":
            # Professional scatter plot
            x_vals = list(range(len(values)))
            ax.scatter(
                x_vals,
                values,
                s=200,
                c=colors[: len(values)],
                alpha=0.7,
                edgecolors="white",
                linewidth=2,
            )

            ax.set_xticks(x_vals)
            ax.set_xticklabels(categories)
            ax.set_xlabel(config["xlabel"], fontsize=14, fontweight="bold")
            ax.set_ylabel(config["ylabel"], fontsize=14, fontweight="bold")
            ax.grid(True, alpha=0.3, linestyle="--")

        elif chart_type == "area":
            # Professional area chart
            x_pos = range(len(values))
            ax.fill_between(x_pos, values, alpha=0.4, color=colors[0])
            ax.plot(x_pos, values, linewidth=2.5, color=colors[1], marker="o", markersize=8)

            ax.set_xticks(x_pos)
            ax.set_xticklabels(categories)
            ax.set_xlabel(config["xlabel"], fontsize=14, fontweight="bold")
            ax.set_ylabel(config["ylabel"], fontsize=14, fontweight="bold")
            ax.grid(True, alpha=0.3, linestyle="--")

        # Set title with enhanced styling
        ax.set_title(config["title"], fontsize=18, fontweight="bold", pad=20, color="#2c3e50")

        # Enhance tick labels
        ax.tick_params(axis="both", which="major", labelsize=11)

        plt.tight_layout()
        # Save with high quality
        plt.savefig(output_file, dpi=150, bbox_inches="tight", facecolor="white", edgecolor="none")
        plt.close()

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, create_chart)

    # Cache the result
    from app.utils.cache import set_cache

    await set_cache("visual", visual_prompt, output_file)
    return output_file


async def render_formula(visual_prompt: str, job_id: str, scene_id: int) -> str:
    """Renders a mathematical formula using LaTeX."""
    output_file = os.path.join(ASSET_STORAGE_PATH, f"job_{job_id}_scene_{scene_id}_formula.png")

    # Extract formula from prompt or use default
    formula = "E = mc^2"  # Default formula

    # Try to extract formula from prompt
    if "formula:" in visual_prompt:
        formula_part = visual_prompt.split("formula:")[1].split("\n")[0].strip()
        if formula_part:
            formula = formula_part
    elif "$" in visual_prompt:
        # Extract math expressions from prompt
        import re

        math_match = re.search(r"\$([^$]+)\$", visual_prompt)
        if math_match:
            formula = math_match.group(1)

    try:
        # Try LaTeX rendering first
        latex_result = await _render_with_latex(formula, output_file, job_id, scene_id)
        if latex_result:
            return latex_result
    except Exception as e:
        logger.warning(
            "LaTeX rendering failed, using matplotlib fallback",
            extra={"scene_id": scene_id, "job_id": job_id, "error": str(e)},
        )

    # Fallback to matplotlib text rendering
    def create_formula():
        fig, ax = plt.subplots(figsize=(10, 6), facecolor="white")
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 6)
        ax.axis("off")

        # Format formula for display
        display_formula = f"${formula}$"

        ax.text(
            5,
            3,
            display_formula,
            fontsize=24,
            ha="center",
            va="center",
            bbox={"boxstyle": "round,pad=0.5", "facecolor": "lightyellow", "alpha": 0.8},
        )

        ax.text(
            5,
            1.5,
            f"Mathematical Formula - Scene {scene_id}",
            ha="center",
            va="center",
            fontsize=14,
            style="italic",
        )

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close()

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, create_formula)

    # Cache the result
    from app.utils.cache import set_cache

    await set_cache("visual", visual_prompt, output_file)
    return output_file


async def render_code(visual_prompt: str, job_id: str, scene_id: int) -> str:
    """Renders a code snippet with syntax highlighting using Pygments."""
    output_file = os.path.join(ASSET_STORAGE_PATH, f"job_{job_id}_scene_{scene_id}_code.png")

    # Extract code from prompt
    code = ""
    language = "python"  # Default language

    if "language:" in visual_prompt:
        lang_part = visual_prompt.split("language:")[1].split("\n")[0].strip()
        if lang_part:
            language = lang_part

    if "code:" in visual_prompt:
        code_part = visual_prompt.split("code:")[1].strip()
        if code_part:
            code = code_part
    elif "```" in visual_prompt:
        # Extract code from markdown code blocks
        import re

        code_match = re.search(r"```(\w+)?\n?(.*?)\n?```", visual_prompt, re.DOTALL)
        if code_match:
            language = code_match.group(1) or "python"
            code = code_match.group(2).strip()

    # Default code if none provided
    if not code:
        code = f"""Scene {scene_id}: Code Example

def generate_visual_asset(scene):
    '''Generate visual assets for video scenes'''
    scene_id = scene.get('id')
    visual_type = scene.get('visual_type')

    if visual_type == 'code':
        return create_code_visual(scene)

    return scene"""

    try:
        # Try Pygments rendering first
        pygments_result = await _render_with_syntax_highlighter(
            code, language, output_file, job_id, scene_id
        )
        if pygments_result:
            return pygments_result
    except Exception as e:
        logger.warning(
            "Pygments rendering failed, using matplotlib fallback",
            extra={"scene_id": scene_id, "job_id": job_id, "error": str(e)},
        )

    # Fallback to matplotlib
    def create_code():
        fig, ax = plt.subplots(figsize=(12, 8), facecolor="#1a1a1a")
        ax.set_facecolor("#1a1a1a")
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 8)
        ax.axis("off")

        # Split code into lines
        code_lines = code.split("\n")

        # Render code with basic syntax highlighting
        for i, line in enumerate(code_lines):
            y_pos = 7 - (i * 0.4)
            if y_pos < 0.5:
                break

            # Simple syntax highlighting
            color = "#d4d4d4"  # default
            if line.strip().startswith("#"):
                color = "#6a9955"  # comment
            elif any(
                keyword in line
                for keyword in ["def ", "class ", "import ", "from ", "if ", "return "]
            ):
                color = "#569cd6"  # keyword
            elif "'" in line or '"' in line:
                color = "#ce9178"  # string

            ax.text(0.5, y_pos, line, fontsize=10, fontfamily="monospace", color=color, va="center")

        # Add title bar
        title_rect = mpatches.Rectangle((0, 7.5), 10, 0.5, facecolor="#2d2d30", alpha=0.9)
        ax.add_patch(title_rect)
        ax.text(
            0.2,
            7.75,
            f"Scene {scene_id}: {language.title()} Code",
            fontsize=12,
            fontweight="bold",
            color="white",
            va="center",
        )

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches="tight", facecolor="#1a1a1a")
        plt.close()

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, create_code)

    # Cache the result
    from app.utils.cache import set_cache

    await set_cache("visual", visual_prompt, output_file)
    return output_file


async def _render_with_mermaid(
    visual_prompt: str, output_file: str, job_id: str, scene_id: int
) -> str | None:
    """
    Render Mermaid diagram to PNG using mermaid-cli (mmdc) if available.
    Falls back to online service if CLI not installed.

    Converts visual_prompt (text description) to valid Mermaid syntax first.
    Returns None on failure to trigger caller's fallback.

    Uses asyncio.create_subprocess_exec to avoid gRPC fork() conflicts.
    """
    import contextlib
    import shutil

    # Convert visual_prompt to valid Mermaid syntax
    mermaid_code = _convert_prompt_to_mermaid(visual_prompt, scene_id)

    if not mermaid_code:
        logger.warning(
            "Failed to convert visual_prompt to Mermaid syntax",
            extra={"scene_id": scene_id, "job_id": job_id},
        )
        return None

    # First, try mmdc CLI (mermaid-cli)
    mmdc = shutil.which("mmdc")
    if mmdc:
        tmp_mmd = os.path.join(ASSET_STORAGE_PATH, f"job_{job_id}_scene_{scene_id}.mmd")
        try:
            # Write mermaid code to temp file
            async with aiofiles.open(tmp_mmd, "w", encoding="utf-8") as f:
                await f.write(mermaid_code)

            logger.info(
                "🎨 Rendering Mermaid diagram with mmdc CLI",
                extra={"scene_id": scene_id, "job_id": job_id, "mermaid_code_preview": mermaid_code[:200]},
            )

            # Use asyncio subprocess to avoid gRPC fork conflicts
            process = await asyncio.create_subprocess_exec(
                mmdc,
                "-i",
                tmp_mmd,
                "-o",
                output_file,
                "-t",
                "default",
                "-b",
                "white",
                "-w",
                "1920",  # Set width for better quality
                "-H",
                "1080",  # Set height
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                # Start new session to isolate from parent process
                start_new_session=True,
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=30.0,  # 30 second timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                raise TimeoutError("mmdc CLI timeout after 30s")

            if process.returncode == 0 and os.path.exists(output_file):
                logger.info(
                    "✅ Mermaid diagram rendered successfully with mmdc CLI",
                    extra={"scene_id": scene_id, "job_id": job_id, "output": output_file, "file_size": os.path.getsize(output_file)},
                )
                return output_file
            else:
                error_msg = (
                    stderr.decode("utf-8", errors="ignore")
                    if stderr
                    else f"Exit code {process.returncode}"
                )
                logger.warning(
                    "⚠️ mmdc CLI failed, will try online service",
                    extra={"scene_id": scene_id, "job_id": job_id, "error": error_msg, "stdout": stdout.decode("utf-8", errors="ignore") if stdout else ""},
                )

        except TimeoutError as e:
            logger.warning(
                "⚠️ mmdc CLI timeout, will try online service",
                extra={"scene_id": scene_id, "job_id": job_id, "error": str(e)},
            )
        except Exception as e:
            logger.warning(
                "⚠️ mmdc CLI error, will try online service",
                extra={"scene_id": scene_id, "job_id": job_id, "error": str(e), "error_type": type(e).__name__},
            )
        finally:
            with contextlib.suppress(Exception):
                if os.path.exists(tmp_mmd):
                    os.remove(tmp_mmd)
    else:
        logger.warning(
            "⚠️ mmdc CLI not found, will use online service. Install with: npm install -g @mermaid-js/mermaid-cli",
            extra={"scene_id": scene_id, "job_id": job_id},
        )

    # Fallback to online service
    try:
        return await _render_mermaid_online(mermaid_code, output_file, job_id, scene_id)
    except Exception as e:
        logger.error(
            "Mermaid rendering failed completely",
            extra={"scene_id": scene_id, "job_id": job_id, "error": str(e)},
        )
        return None


def _convert_prompt_to_mermaid(visual_prompt: str, scene_id: int) -> str:
    """
    Convert visual_prompt (text description) to valid Mermaid diagram syntax.

    Supports:
    - Flowcharts (process flow, workflow)
    - Sequence diagrams (interactions, communication)
    - Class diagrams (structure, relationships)
    - State diagrams (states, transitions)
    - ER diagrams (data models)

    Returns valid Mermaid code or empty string if conversion fails.
    """
    import re

    prompt_lower = visual_prompt.lower()

    # Check if already contains Mermaid syntax
    if any(
        keyword in prompt_lower
        for keyword in [
            "flowchart",
            "sequencediagram",
            "classDiagram",
            "stateDiagram",
            "erDiagram",
            "graph TD",
            "graph LR",
            "```mermaid",
        ]
    ):
        # Extract Mermaid code if wrapped in code blocks
        mermaid_match = re.search(r"```mermaid\s+(.*?)\s+```", visual_prompt, re.DOTALL)
        if mermaid_match:
            return mermaid_match.group(1).strip()
        return visual_prompt.strip()

    # Detect diagram type from keywords
    if any(
        keyword in prompt_lower for keyword in ["flow", "process", "workflow", "steps", "procedure"]
    ):
        return _create_flowchart_from_prompt(visual_prompt, scene_id)

    elif any(
        keyword in prompt_lower
        for keyword in ["sequence", "interaction", "communication", "message"]
    ):
        return _create_sequence_diagram_from_prompt(visual_prompt, scene_id)

    elif any(keyword in prompt_lower for keyword in ["class", "object", "inheritance", "method"]):
        return _create_class_diagram_from_prompt(visual_prompt, scene_id)

    elif any(keyword in prompt_lower for keyword in ["state", "status", "transition", "lifecycle"]):
        return _create_state_diagram_from_prompt(visual_prompt, scene_id)

    elif any(
        keyword in prompt_lower
        for keyword in ["entity", "relationship", "database", "table", "model"]
    ):
        return _create_er_diagram_from_prompt(visual_prompt, scene_id)

    # Default: create flowchart
    return _create_flowchart_from_prompt(visual_prompt, scene_id)


def _create_flowchart_from_prompt(prompt: str, scene_id: int) -> str:
    """Create a flowchart from text description with improved parsing."""
    import re

    # Extract steps/items from prompt
    lines = [line.strip() for line in prompt.split("\n") if line.strip()]

    # Filter out meta instructions (skip lines starting with common instruction keywords)
    instruction_keywords = [
        "diagram type:",
        "visual:",
        "style:",
        "note:",
        "arrows:",
        "use ",
        "add ",
        "label ",
        "include ",
        "flowchart",
        "graph ",
    ]
    filtered_lines = []
    for line in lines:
        line_lower = line.lower()
        # Skip instruction lines
        if any(line_lower.startswith(kw) for kw in instruction_keywords):
            continue
        # Skip very short lines and headers ending with ":" (unless it's meaningful content)
        if len(line) <= 3:
            continue
        # Keep lines ending with ":" if they're longer (could be labels)
        if line.endswith(":") and len(line) <= 15:
            continue
        filtered_lines.append(line)

    # Try to find numbered or bulleted lists
    steps = []
    for line in filtered_lines:
        # Match patterns like "1. Step", "- Step", "* Step", "• Step"
        match = re.match(r"^[\d\-\*\•]+[\.\):]?\s+(.+)$", line)
        if match:
            content = match.group(1)
            # Extract just the main text before parentheses/brackets
            content = re.split(r"\s*[\(\[]", content)[0]
            steps.append(content.strip())
        elif line and not any(line.lower().startswith(kw) for kw in instruction_keywords):
            # If not matched but not empty and not an instruction, add it
            steps.append(line.strip())

    if not steps or len(steps) < 2:
        # Fallback: Try to extract any meaningful content
        steps = [line for line in filtered_lines if len(line) > 5][:5]
        
    if not steps or len(steps) < 2:
        # Final fallback: Create simple 3-step process
        steps = ["Start", "Process Data", "Complete"]

    # Build flowchart with properly formatted nodes
    mermaid_code = "flowchart TD\n"

    # Create nodes with cleaned text
    for i, step in enumerate(steps[:10]):  # Max 10 steps
        node_id = chr(65 + i)  # A, B, C, ...
        # Clean step text - remove special chars that break Mermaid
        clean_step = (
            step.replace('"', "'")
            .replace("[", "(")
            .replace("]", ")")
            .replace("{", "(")
            .replace("}", ")")
            .replace("&", "and")
            .replace("#", "No.")
            [:60]  # Increased length limit
            .strip()
        )

        # Ensure non-empty
        if not clean_step:
            clean_step = f"Step {i + 1}"

        mermaid_code += f"    {node_id}[\"{clean_step}\"]\n"

    # Add arrows between steps
    for i in range(len(steps) - 1):
        if i >= 9:
            break
        node_from = chr(65 + i)
        node_to = chr(65 + i + 1)
        mermaid_code += f"    {node_from} --> {node_to}\n"

    logger.debug(
        f"Generated flowchart with {len(steps)} steps from prompt",
        extra={"steps_count": len(steps), "scene_id": scene_id}
    )

    return mermaid_code


def _create_sequence_diagram_from_prompt(prompt: str, scene_id: int) -> str:
    """Create a sequence diagram from text description."""
    # Simple sequence diagram template
    mermaid_code = "sequenceDiagram\n"
    mermaid_code += "    participant A as User\n"
    mermaid_code += "    participant B as System\n"
    mermaid_code += "    participant C as Database\n"
    mermaid_code += "    A->>B: Request\n"
    mermaid_code += "    B->>C: Query\n"
    mermaid_code += "    C-->>B: Data\n"
    mermaid_code += "    B-->>A: Response\n"
    return mermaid_code


def _create_class_diagram_from_prompt(prompt: str, scene_id: int) -> str:
    """Create a class diagram from text description."""
    mermaid_code = "classDiagram\n"
    mermaid_code += "    class MainClass {\n"
    mermaid_code += "        +attribute1\n"
    mermaid_code += "        +attribute2\n"
    mermaid_code += "        +method1()\n"
    mermaid_code += "        +method2()\n"
    mermaid_code += "    }\n"
    mermaid_code += "    class SubClass {\n"
    mermaid_code += "        +property\n"
    mermaid_code += "        +function()\n"
    mermaid_code += "    }\n"
    mermaid_code += "    MainClass <|-- SubClass\n"
    return mermaid_code


def _create_state_diagram_from_prompt(prompt: str, scene_id: int) -> str:
    """Create a state diagram from text description."""
    mermaid_code = "stateDiagram-v2\n"
    mermaid_code += "    [*] --> Initial\n"
    mermaid_code += "    Initial --> Processing\n"
    mermaid_code += "    Processing --> Complete\n"
    mermaid_code += "    Processing --> Error\n"
    mermaid_code += "    Error --> Processing\n"
    mermaid_code += "    Complete --> [*]\n"
    return mermaid_code


def _create_er_diagram_from_prompt(prompt: str, scene_id: int) -> str:
    """Create an ER diagram from text description."""
    mermaid_code = "erDiagram\n"
    mermaid_code += "    USER ||--o{ ORDER : places\n"
    mermaid_code += "    ORDER ||--|{ ORDER_ITEM : contains\n"
    mermaid_code += "    PRODUCT ||--o{ ORDER_ITEM : includes\n"
    mermaid_code += "    USER {\n"
    mermaid_code += "        string id\n"
    mermaid_code += "        string name\n"
    mermaid_code += "        string email\n"
    mermaid_code += "    }\n"
    return mermaid_code


async def _render_mermaid_online(
    mermaid_code: str, output_file: str, job_id: str, scene_id: int
) -> str:
    """Render Mermaid diagram using online service as fallback."""
    try:
        import httpx  # Use httpx for async support

        # Use mermaid.ink service (encode diagram in URL)
        import base64
        import json as json_module

        mermaid_ink_url = os.environ.get("MERMAID_INK_SERVER", "https://mermaid.ink")

        # Encode the mermaid code as base64 for URL
        # mermaid.ink expects: https://mermaid.ink/img/{base64_encoded_json}
        mermaid_json = json_module.dumps({"code": mermaid_code, "mermaid": {"theme": "default"}})
        encoded = base64.b64encode(mermaid_json.encode()).decode()

        logger.info(
            "🌐 Rendering Mermaid diagram via online service (mermaid.ink)",
            extra={"scene_id": scene_id, "job_id": job_id, "service_url": mermaid_ink_url},
        )

        # Make GET request to mermaid.ink with encoded diagram (with timeout)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{mermaid_ink_url}/img/{encoded}")

            if response.status_code == 200:
                # mermaid.ink returns PNG directly
                png_data = response.content

                async with aiofiles.open(output_file, "wb") as f:
                    await f.write(png_data)

                logger.info(
                    "✅ Mermaid diagram rendered successfully via online service",
                    extra={"scene_id": scene_id, "job_id": job_id, "output_file": output_file, "file_size": len(png_data)},
                )

                return output_file
            else:
                logger.error(
                    "❌ Online Mermaid service failed",
                    extra={
                        "scene_id": scene_id,
                        "job_id": job_id,
                        "status_code": response.status_code,
                        "response": response.text[:200],
                    },
                )
                raise Exception(f"Online service failed with status {response.status_code}")

    except Exception as e:
        logger.error(
            "❌ Online Mermaid rendering failed, using text-based fallback",
            extra={"scene_id": scene_id, "job_id": job_id, "error": str(e), "error_type": type(e).__name__},
        )

        # Final fallback to text representation
        await _render_mermaid_fallback(mermaid_code, output_file, scene_id)
        return output_file


async def _render_mermaid_fallback(mermaid_code: str, output_file: str, scene_id: int) -> None:
    """Create a fallback text-based representation of Mermaid diagram."""
    fig, ax = plt.subplots(figsize=(12, 8), facecolor="white")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis("off")

    # Title
    ax.text(
        5,
        7.5,
        f"Mermaid Diagram - Scene {scene_id}",
        fontsize=18,
        fontweight="bold",
        ha="center",
        va="center",
        color="#2c3e50",
    )

    # Parse and display mermaid code in a simple way
    lines = mermaid_code.split("\n")
    y_pos = 6.5

    for line in lines[:8]:  # Show first 8 lines
        if y_pos < 1:
            break

        # Simple syntax highlighting
        color = "#2c3e50"
        if line.strip().startswith("graph ") or line.strip().startswith("flowchart "):
            color = "#e74c3c"
        elif "-->" in line or "---" in line:
            color = "#3498db"

        ax.text(0.5, y_pos, line, fontsize=10, fontfamily="monospace", color=color, va="center")
        y_pos -= 0.4

    # Add note about installation
    ax.text(
        5,
        1,
        "[INFO] Install mermaid-cli for better rendering:\n   npm install -g @mermaid-js/mermaid-cli",
        ha="center",
        va="center",
        fontsize=8,
        style="italic",
        color="#7f8c8d",
    )

    # Add sample mermaid syntax hint
    ax.text(
        5,
        0.3,
        "Example: graph TD; A-->B; B-->C;",
        ha="center",
        va="center",
        fontsize=7,
        color="#95a5a6",
    )

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()


async def _render_with_graphviz(dot_code: str, output_file: str, job_id: str, scene_id: int) -> str:
    """Render Graphviz diagram to PNG."""
    try:
        import subprocess

        # Create temporary dot file
        temp_dot = os.path.join(ASSET_STORAGE_PATH, f"temp_{job_id}_{scene_id}.dot")

        with open(temp_dot, "w") as f:
            f.write(dot_code)

        # Use graphviz to render
        subprocess.run(
            ["dot", "-Tpng", temp_dot, "-o", output_file], check=True, capture_output=True
        )

        # Clean up temp file
        os.remove(temp_dot)

        logger.info(
            "Graphviz diagram rendered successfully",
            extra={"scene_id": scene_id, "job_id": job_id, "output_file": output_file},
        )

        return output_file

    except subprocess.CalledProcessError as e:
        logger.error(
            "Graphviz rendering failed",
            extra={"scene_id": scene_id, "job_id": job_id, "error": str(e)},
        )
    except FileNotFoundError:
        logger.error("Graphviz not installed", extra={"scene_id": scene_id, "job_id": job_id})
    except Exception as e:
        logger.error(
            "Graphviz rendering error",
            extra={"scene_id": scene_id, "job_id": job_id, "error": str(e)},
        )

    return None


async def _render_with_latex(
    formula: str, output_file: str, job_id: str, scene_id: int
) -> str | None:
    """
    Render LaTeX formula to PNG using Matplotlib's TeX rendering.
    Falls back to MathText if TeX not available.
    Returns None on failure to trigger caller's fallback.
    """
    import matplotlib.pyplot as plt

    try:
        fig, ax = plt.subplots(figsize=(10, 6), facecolor="white")
        ax.axis("off")

        # Try rendering with TeX (requires LaTeX installation)
        try:
            plt.rc("text", usetex=True)
            ax.text(
                0.5,
                0.5,
                f"${formula}$",
                fontsize=28,
                ha="center",
                va="center",
                transform=ax.transAxes,
            )
            logger.info(
                "Rendering formula with LaTeX",
                extra={"scene_id": scene_id, "job_id": job_id},
            )
        except Exception:
            # Fallback to MathText (built-in, no LaTeX needed)
            plt.rc("text", usetex=False)
            ax.text(
                0.5,
                0.5,
                f"${formula}$",
                fontsize=28,
                ha="center",
                va="center",
                transform=ax.transAxes,
            )
            logger.info(
                "Rendering formula with MathText fallback",
                extra={"scene_id": scene_id, "job_id": job_id},
            )

        plt.savefig(output_file, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)

        logger.info(
            "Formula rendered successfully",
            extra={"scene_id": scene_id, "job_id": job_id, "output": output_file},
        )
        return output_file

    except Exception as e:
        plt.close(fig) if "fig" in locals() else None
        logger.error(
            "Formula rendering failed",
            extra={"scene_id": scene_id, "job_id": job_id, "error": str(e)},
        )
        return None


async def _render_with_syntax_highlighter(
    code: str, language: str, output_file: str, job_id: str, scene_id: int
) -> str | None:
    """
    Render code with professional syntax highlighting using Pygments' ImageFormatter.
    Uses high-quality settings with line numbers and modern themes.
    Returns None on failure to trigger caller's fallback.
    """
    try:
        from pygments import highlight
        from pygments.formatters.img import ImageFormatter
        from pygments.lexers import TextLexer, get_lexer_by_name
        from app.core.config import settings

        # Get appropriate lexer
        try:
            lexer = get_lexer_by_name(language) if language else TextLexer()
        except Exception:
            logger.warning(f"Could not find lexer for language '{language}', using TextLexer")
            lexer = TextLexer()

        # Detect theme preference from visual_prompt if any
        # Support multiple professional themes
        available_themes = {
            "dark": "monokai",  # Default dark theme
            "light": "github-dark",  # Light theme
            "vs": "vs",  # Visual Studio
            "dracula": "dracula",  # Dracula theme
            "nord": "nord",  # Nord theme
            "solarized": "solarized-dark",  # Solarized
        }

        theme = "monokai"  # Default to monokai (professional dark theme)

        # Try multiple monospace fonts in order of preference
        # macOS: SF Mono, Menlo, Monaco
        # Linux: Fira Code, DejaVu Sans Mono
        # Windows: Consolas, Courier New
        available_fonts = [
            "SF Mono",
            "Menlo",
            "Monaco",  # macOS
            "Fira Code",
            "Fira Mono",
            "DejaVu Sans Mono",  # Linux
            "Consolas",
            "Courier New",  # Windows
            "monospace",  # Fallback
        ]
        font_to_use = available_fonts[2]  # Default to Monaco (widely available)

        # High-quality formatter settings
        formatter = ImageFormatter(
            font_name=font_to_use,
            font_size=16,  # Larger for better readability
            line_numbers=True,  # Show line numbers
            line_number_fg="#888888",  # Gray line numbers
            line_number_bg="#2d2d30",  # Dark background for line numbers
            line_number_bold=False,
            line_number_pad=6,  # Padding between line numbers and code
            style=theme,
            image_pad=20,  # Padding around the code
            line_pad=4,  # Padding between lines
        )

        # Generate highlighted code
        png_bytes = highlight(code, lexer, formatter)

        # Save the high-quality output
        with open(output_file, "wb") as f:
            f.write(png_bytes)

        # Optionally resize/enhance the image for video (1920x1080 target)
        try:
            from PIL import Image

            img = Image.open(output_file)

            # If image is smaller than 1920 width, upscale it
            if img.width < settings.SLIDE_WIDTH:
                # Calculate height to maintain aspect ratio
                ratio = settings.SLIDE_WIDTH / img.width
                new_height = int(img.height * ratio)

                # Resize with high-quality resampling
                img_resized = img.resize(
                    (settings.SLIDE_WIDTH, new_height), Image.Resampling.LANCZOS
                )

                # If height exceeds SLIDE_HEIGHT, crop from center
                if new_height > settings.SLIDE_HEIGHT:
                    top = (new_height - settings.SLIDE_HEIGHT) // 2
                    img_resized = img_resized.crop(
                        (0, top, settings.SLIDE_WIDTH, top + settings.SLIDE_HEIGHT)
                    )
                # If height is less, pad with theme background color
                elif new_height < settings.SLIDE_HEIGHT:
                    from PIL import ImageOps

                    # Pad with dark background for dark themes
                    bg_color = (
                        (42, 42, 42)
                        if theme in ["monokai", "dracula", "nord", "solarized-dark"]
                        else (255, 255, 255)
                    )
                    img_resized = ImageOps.pad(
                        img_resized, (settings.SLIDE_WIDTH, settings.SLIDE_HEIGHT), color=bg_color
                    )

                # Save the resized image
                img_resized.save(output_file, "PNG", quality=settings.IMAGE_QUALITY)
            else:
                img.save(output_file, "PNG", quality=settings.IMAGE_QUALITY)

        except ImportError:
            logger.warning("PIL not available, skipping image optimization")
        except Exception as e:
            logger.warning(f"Image optimization failed: {e}, using original")

        logger.info(
            "Code syntax highlighting completed",
            extra={
                "scene_id": scene_id,
                "job_id": job_id,
                "language": lexer.name,
                "theme": theme,
                "output_file": output_file,
            },
        )
        return output_file

    except ImportError as e:
        logger.error(f"Pygments not installed: {e}", extra={"scene_id": scene_id, "job_id": job_id})
        return None
    except Exception as e:
        logger.error(
            "Syntax highlighting failed",
            extra={"scene_id": scene_id, "job_id": job_id, "error": str(e)},
        )
        return None
