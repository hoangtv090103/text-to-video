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
        '#': 'No.',
        '$': '\\$',
        '%': '\\%',
        '&': '\\&',
        '_': '\\_',
        '{': '\\{',
        '}': '\\}',
        '^': '\\^{}',
        '~': '\\~{}',
        '\\': '\\textbackslash{}'
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


async def call_presenton_api(visual_prompt: str, job_id: str, scene_id: int) -> str:
    """
    Call Presenton API to generate presentation slides.
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

    try:
        # Get Presenton service URL from environment or use default
        presenton_url = os.environ.get("PRESENTON_URL", "http://localhost:9000")

        # Prepare request payload for Presenton API
        request_payload = {
            "content": visual_prompt,
            "n_slides": 1,  # Generate only one slide for this scene
            "language": "English",
            "template": "general",
            "export_as": "pdf",  # We'll convert the first slide to PNG
        }

        async with httpx.AsyncClient() as client:
            # Call Presenton generate presentation API
            response = await client.post(
                f"{presenton_url}/api/v1/ppt/presentation/generate",
                json=request_payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code != 200:
                logger.error(
                    "Presenton API failed",
                    extra={"status_code": response.status_code, "response": response.text[:500]},
                )
                raise Exception(f"Presenton API failed with status {response.status_code}")

            result = response.json()
            presentation_path = result.get("path")

            if not presentation_path:
                raise Exception("No presentation path returned from Presenton API")

            # Download the generated presentation file
            # Save the PDF temporarily with streaming download
            temp_pdf_path = os.path.join(ASSET_STORAGE_PATH, f"temp_{job_id}_{scene_id}.pdf")

            async with client.stream("GET", f"{presenton_url}{presentation_path}") as download_response:
                if download_response.status_code != 200:
                    raise Exception(f"Failed to download presentation: {download_response.status_code}")

                async with aiofiles.open(temp_pdf_path, 'wb') as f:
                    async for chunk in download_response.aiter_bytes(chunk_size=8192):
                        await f.write(chunk)

            # Convert first page of PDF to PNG using subprocess
            def convert_pdf_to_png():
                import subprocess

                try:
                    # Use ImageMagick to convert first page of PDF to PNG
                    subprocess.run(
                        [
                            "convert",
                            f"{temp_pdf_path}[0]",  # [0] means first page only
                            "-density",
                            "150",
                            "-quality",
                            "90",
                            output_file,
                        ],
                        check=True,
                        capture_output=True,
                    )

                    # Clean up temporary PDF
                    os.remove(temp_pdf_path)

                except subprocess.CalledProcessError as e:
                    logger.error("Failed to convert PDF to PNG", extra={"error": str(e)})
                    # Fallback: create a simple slide if conversion fails
                    create_fallback_slide()
                except FileNotFoundError:
                    logger.warning("ImageMagick not found, creating fallback slide")
                    # Fallback: create a simple slide if ImageMagick is not available
                    create_fallback_slide()

            def create_fallback_slide():
                # Create a simple slide as fallback
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
                    ax.text(
                        8, y_pos, line[:80], fontsize=16, ha="center", va="center", color="#2d3748"
                    )

                plt.tight_layout()
                plt.savefig(output_file, dpi=150, bbox_inches="tight", facecolor="white")
                plt.close()

            # Run conversion in executor to avoid blocking
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, convert_pdf_to_png)

            logger.info(
                "Slide generated successfully via Presenton API",
                extra={"scene_id": scene_id, "job_id": job_id, "output_file": output_file},
            )

            # Cache the successful result
            await set_cache("visual", visual_prompt, output_file)

    except Exception as e:
        logger.error(
            "Failed to generate slide via Presenton API, using fallback",
            extra={"scene_id": scene_id, "job_id": job_id, "error": str(e)},
        )

        # Fallback to simple slide generation
        def create_fallback_slide():
            fig, ax = plt.subplots(figsize=(19.2, 10.8), facecolor="white", dpi=100)
            ax.set_xlim(0, 16)
            ax.set_ylim(0, 9)
            ax.axis("off")

            # Simple background with gradient
            gradient = np.linspace(0, 1, 256).reshape(1, -1)
            gradient = np.vstack((gradient, gradient))
            ax.imshow(gradient, extent=(0, 16, 0, 9), aspect="auto", cmap="Blues_r", alpha=0.1)

            # Title section
            title_text = f"Scene {scene_id}: Professional Presentation"
            ax.text(
                8,
                7.5,
                title_text,
                fontsize=36,
                fontweight="bold",
                ha="center",
                va="center",
                color="#1a365d",
            )

            # Content area
            content_lines = visual_prompt.split("\n")[:4]
            for i, line in enumerate(content_lines[:3]):
                y_pos = 6 - (i * 0.8)
                ax.text(8, y_pos, line[:80], fontsize=18, ha="center", va="center", color="#2d3748")

            # Accent elements
            accent_bar = mpatches.Rectangle((0.5, 1), 0.2, 7, facecolor="#4299e1", alpha=0.8)
            ax.add_patch(accent_bar)

            brand_rect = mpatches.Rectangle((0, 0), 16, 1.5, facecolor="#1a365d", alpha=0.05)
            ax.add_patch(brand_rect)

            plt.tight_layout()
            plt.savefig(output_file, dpi=150, bbox_inches="tight", facecolor="white")
            plt.close()
        # Run fallback in executor
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, create_fallback_slide)

    # Cache the result (both success and fallback)
    from app.utils.cache import set_cache
    await set_cache("visual", visual_prompt, output_file)
    return output_file


async def render_diagram(visual_prompt: str, job_id: str, scene_id: int) -> str:
    """Renders a diagram using Mermaid service."""
    output_file = os.path.join(ASSET_STORAGE_PATH, f"job_{job_id}_scene_{scene_id}_diagram.png")

    try:
        # Try to use Mermaid service
        mermaid_result = await _render_with_mermaid(visual_prompt, output_file, job_id, scene_id)
        if mermaid_result:
            return mermaid_result
    except Exception as e:
        logger.warning(
            "Mermaid rendering failed, using matplotlib fallback",
            extra={"scene_id": scene_id, "job_id": job_id, "error": str(e)},
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

    # Cache the result
    from app.utils.cache import set_cache
    await set_cache("visual", visual_prompt, output_file)
    return output_file


async def generate_graph(visual_prompt: str, job_id: str, scene_id: int) -> str:
    """Generates a chart/graph using matplotlib with enhanced features."""
    output_file = os.path.join(ASSET_STORAGE_PATH, f"job_{job_id}_scene_{scene_id}_chart.png")

    # Check cache first
    from app.utils.cache import get_from_cache, set_cache
    cached_result = await get_from_cache("visual", visual_prompt)
    if cached_result and os.path.exists(cached_result):
        logger.info("Using cached visual asset", extra={"cached_path": cached_result})
        return cached_result

    def create_chart():
        fig, ax = plt.subplots(figsize=(12, 8), facecolor="white")

        # Enhanced sample data based on prompt
        if "bar" in visual_prompt.lower() or "column" in visual_prompt.lower():
            categories = ["Q1", "Q2", "Q3", "Q4"]
            values = [65, 78, 90, 72]
            title = "Quarterly Performance"
        elif "line" in visual_prompt.lower():
            x = [1, 2, 3, 4, 5, 6]
            y = [10, 25, 18, 35, 28, 42]
            ax.plot(x, y, marker="o", linewidth=3, markersize=8)
            ax.set_title(f"Line Chart - Scene {scene_id}", fontsize=16, fontweight="bold", pad=20)
            ax.set_xlabel("Time Period", fontsize=12)
            ax.set_ylabel("Values", fontsize=12)
            ax.grid(True, alpha=0.3)
        elif "pie" in visual_prompt.lower():
            labels = ["Category A", "Category B", "Category C", "Category D"]
            sizes = [35, 25, 20, 20]
            colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"]
            ax.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%", startangle=90)
            ax.set_title(f"Pie Chart - Scene {scene_id}", fontsize=16, fontweight="bold", pad=20)
        else:
            # Default bar chart
            categories = ["A", "B", "C", "D", "E"]
            values = [23, 45, 56, 78, 32]
            title = f"Chart for Scene {scene_id}"

        if "line" not in visual_prompt.lower() and "pie" not in visual_prompt.lower():
            bars = ax.bar(
                categories, values, color=["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"]
            )
            ax.set_title(title, fontsize=16, fontweight="bold", pad=20)
            ax.set_xlabel("Categories", fontsize=12)
            ax.set_ylabel("Values", fontsize=12)

            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.annotate(
                    f"{height}",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                )

            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches="tight", facecolor="white")
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
    mermaid_code: str, output_file: str, job_id: str, scene_id: int
) -> str | None:
    """
    Render Mermaid diagram to PNG using mermaid-cli (mmdc) if available.
    Falls back to online service if CLI not installed.
    Returns None on failure to trigger caller's fallback.
    """
    import contextlib
    import shutil
    from subprocess import CalledProcessError, run

    # First, try mmdc CLI (mermaid-cli)
    mmdc = shutil.which("mmdc")
    if mmdc:
        tmp_mmd = os.path.join(ASSET_STORAGE_PATH, f"job_{job_id}_scene_{scene_id}.mmd")
        try:
            with open(tmp_mmd, "w", encoding="utf-8") as f:
                f.write(mermaid_code)

            logger.info(
                "Rendering Mermaid with mmdc CLI",
                extra={"scene_id": scene_id, "job_id": job_id},
            )

            run(
                [mmdc, "-i", tmp_mmd, "-o", output_file, "-t", "default", "-b", "white"],
                check=True,
                capture_output=True,
            )

            logger.info(
                "Mermaid rendered successfully with mmdc",
                extra={"scene_id": scene_id, "job_id": job_id, "output": output_file},
            )
            return output_file

        except CalledProcessError as e:
            logger.warning(
                "mmdc CLI failed",
                extra={"scene_id": scene_id, "job_id": job_id, "error": str(e)},
            )
        finally:
            with contextlib.suppress(Exception):
                os.remove(tmp_mmd)

    # Fallback to online service
    try:
        return await _render_mermaid_online(mermaid_code, output_file, job_id, scene_id)
    except Exception as e:
        logger.error(
            "Mermaid rendering failed completely",
            extra={"scene_id": scene_id, "job_id": job_id, "error": str(e)},
        )
        return None


async def _render_mermaid_online(
    mermaid_code: str, output_file: str, job_id: str, scene_id: int
) -> str:
    """Render Mermaid diagram using online service as fallback."""
    try:
        import requests

        # Use mermaid.ink service (encode diagram in URL)
        import base64
        import json as json_module

        mermaid_ink_url = os.environ.get("MERMAID_INK_SERVER", "https://mermaid.ink")

        # Encode the mermaid code as base64 for URL
        # mermaid.ink expects: https://mermaid.ink/img/{base64_encoded_json}
        mermaid_json = json_module.dumps({"code": mermaid_code, "mermaid": {"theme": "default"}})
        encoded = base64.b64encode(mermaid_json.encode()).decode()

        logger.info(
            "Rendering Mermaid diagram via online service",
            extra={"scene_id": scene_id, "job_id": job_id, "service_url": mermaid_ink_url},
        )

        # Make GET request to mermaid.ink with encoded diagram
        response = requests.get(f"{mermaid_ink_url}/img/{encoded}", timeout=30)

        if response.status_code == 200:
            # mermaid.ink returns PNG directly
            png_data = response.content

            with open(output_file, "wb") as f:
                f.write(png_data)

            logger.info(
                "Mermaid diagram rendered successfully via online service",
                extra={"scene_id": scene_id, "job_id": job_id, "output_file": output_file},
            )

            return output_file
        else:
            logger.error(
                "Online Mermaid service failed",
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
            "Online Mermaid rendering failed",
            extra={"scene_id": scene_id, "job_id": job_id, "error": str(e)},
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
    Render code with syntax highlighting using Pygments' ImageFormatter.
    Returns None on failure to trigger caller's fallback.
    """
    try:
        from pygments import highlight
        from pygments.formatters.img import ImageFormatter
        from pygments.lexers import TextLexer, get_lexer_by_name

        # Get appropriate lexer
        try:
            lexer = get_lexer_by_name(language) if language else TextLexer()
        except Exception:
            lexer = TextLexer()

        # Render code to PNG using ImageFormatter
        # Try multiple monospace fonts in order of preference
        available_fonts = ["Monaco", "Courier New", "Courier", "monospace"]
        font_to_use = available_fonts[0]  # Default to Monaco for macOS

        formatter = ImageFormatter(
            font_name=font_to_use,
            font_size=14,
            line_numbers=False,
            style="monokai",
        )
        png_bytes = highlight(code, lexer, formatter)

        with open(output_file, "wb") as f:
            f.write(png_bytes)

        logger.info(
            "Code syntax highlighting completed",
            extra={
                "scene_id": scene_id,
                "job_id": job_id,
                "language": lexer.name,
                "output_file": output_file,
            },
        )
        return output_file

    except ImportError:
        logger.error("Pygments not installed", extra={"scene_id": scene_id, "job_id": job_id})
        return None
    except Exception as e:
        logger.error(
            "Syntax highlighting failed",
            extra={"scene_id": scene_id, "job_id": job_id, "error": str(e)},
        )
        return None
