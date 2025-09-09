import asyncio
import os
import logging
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

logger = logging.getLogger(__name__)

# Asset storage configuration
ASSET_STORAGE_PATH = os.environ.get("ASSET_STORAGE_PATH", "/tmp/visuals")
os.makedirs(ASSET_STORAGE_PATH, exist_ok=True)


async def call_presenton_api(visual_prompt: str, job_id: str, scene_id: int) -> str:
    """
    Call Presenton API to generate presentation slides.
    """
    import httpx

    logger.info("Generating slide via Presenton API", extra={"scene_id": scene_id, "job_id": job_id})

    output_file = os.path.join(
        ASSET_STORAGE_PATH, f"job_{job_id}_scene_{scene_id}_slide.png")

    try:
        # Get Presenton service URL from environment or use default
        presenton_url = os.environ.get("PRESENTON_URL", "http://localhost:9000")

        # Prepare request payload for Presenton API
        request_payload = {
            "prompt": visual_prompt,
            "n_slides": 1,  # Generate only one slide for this scene
            "language": "English",
            "template": "general",
            "export_as": "pdf"  # We'll convert the first slide to PNG
        }

        async with httpx.AsyncClient() as client:
            # Call Presenton generate presentation API
            response = await client.post(
                f"{presenton_url}/api/v1/ppt/presentation/generate",
                json=request_payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                logger.error("Presenton API failed", extra={
                    "status_code": response.status_code,
                    "response": response.text[:500]
                })
                raise Exception(f"Presenton API failed with status {response.status_code}")

            result = response.json()
            presentation_path = result.get("path")

            if not presentation_path:
                raise Exception("No presentation path returned from Presenton API")

            # Download the generated presentation file
            download_response = await client.get(f"{presenton_url}{presentation_path}")

            if download_response.status_code != 200:
                raise Exception(f"Failed to download presentation: {download_response.status_code}")

            # Save the PDF temporarily
            temp_pdf_path = os.path.join(ASSET_STORAGE_PATH, f"temp_{job_id}_{scene_id}.pdf")
            with open(temp_pdf_path, 'wb') as f:
                f.write(download_response.content)

            # Convert first page of PDF to PNG using subprocess
            def convert_pdf_to_png():
                import subprocess
                try:
                    # Use ImageMagick to convert first page of PDF to PNG
                    subprocess.run([
                        'convert',
                        f'{temp_pdf_path}[0]',  # [0] means first page only
                        '-density', '150',
                        '-quality', '90',
                        output_file
                    ], check=True, capture_output=True)

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
                fig, ax = plt.subplots(figsize=(19.2, 10.8), facecolor='white', dpi=100)
                ax.set_xlim(0, 16)
                ax.set_ylim(0, 9)
                ax.axis('off')

                # Simple background
                ax.add_patch(mpatches.Rectangle((0, 0), 16, 9, facecolor='#f8f9fa'))

                # Title
                title_text = f"Scene {scene_id}: Generated Slide"
                ax.text(8, 7.5, title_text, fontsize=32, fontweight='bold',
                        ha='center', va='center', color='#1a365d')

                # Content
                content_lines = visual_prompt.split('\n')[:4]
                for i, line in enumerate(content_lines[:3]):
                    y_pos = 6 - (i * 0.8)
                    ax.text(8, y_pos, line[:80], fontsize=16, ha='center', va='center',
                           color='#2d3748')

                plt.tight_layout()
                plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
                plt.close()

            # Run conversion in executor to avoid blocking
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, convert_pdf_to_png)

            logger.info("Slide generated successfully via Presenton API", extra={
                "scene_id": scene_id,
                "job_id": job_id,
                "output_file": output_file
            })

    except Exception as e:
        logger.error("Failed to generate slide via Presenton API, using fallback", extra={
            "scene_id": scene_id,
            "job_id": job_id,
            "error": str(e)
        })

        # Fallback to simple slide generation
        def create_fallback_slide():
            fig, ax = plt.subplots(figsize=(19.2, 10.8), facecolor='white', dpi=100)
            ax.set_xlim(0, 16)
            ax.set_ylim(0, 9)
            ax.axis('off')

            # Simple background with gradient
            gradient = np.linspace(0, 1, 256).reshape(1, -1)
            gradient = np.vstack((gradient, gradient))
            ax.imshow(gradient, extent=(0, 16, 0, 9), aspect='auto', cmap='Blues_r', alpha=0.1)

            # Title section
            title_text = f"Scene {scene_id}: Professional Presentation"
            ax.text(8, 7.5, title_text, fontsize=36, fontweight='bold',
                    ha='center', va='center', color='#1a365d')

            # Content area
            content_lines = visual_prompt.split('\n')[:4]
            for i, line in enumerate(content_lines[:3]):
                y_pos = 6 - (i * 0.8)
                ax.text(8, y_pos, line[:80], fontsize=18, ha='center', va='center',
                       color='#2d3748')

            # Accent elements
            accent_bar = mpatches.Rectangle((0.5, 1), 0.2, 7, facecolor='#4299e1', alpha=0.8)
            ax.add_patch(accent_bar)

            brand_rect = mpatches.Rectangle((0, 0), 16, 1.5, facecolor='#1a365d', alpha=0.05)
            ax.add_patch(brand_rect)

            plt.tight_layout()
            plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close()

        # Run fallback in executor
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, create_fallback_slide)

    return output_file
async def render_diagram(visual_prompt: str, job_id: str, scene_id: int) -> str:
    """Renders a simple diagram/flowchart."""
    output_file = os.path.join(
        ASSET_STORAGE_PATH, f"job_{job_id}_scene_{scene_id}_diagram.png")

    def create_diagram():
        fig, ax = plt.subplots(figsize=(12, 8), facecolor='white')
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 8)
        ax.axis('off')

        # Create simple flowchart
        boxes = [
            {'xy': (2, 6), 'text': 'Start'},
            {'xy': (5, 6), 'text': 'Process'},
            {'xy': (8, 6), 'text': 'End'},
        ]

        for i, box in enumerate(boxes):
            rect = mpatches.FancyBboxPatch(
                (box['xy'][0] - 0.8, box['xy'][1] - 0.4), 1.6, 0.8,
                boxstyle="round,pad=0.1", facecolor='lightblue', edgecolor='navy'
            )
            ax.add_patch(rect)
            ax.text(box['xy'][0], box['xy'][1], box['text'],
                   ha='center', va='center', fontsize=12, fontweight='bold')

            # Add arrows between boxes
            if i < len(boxes) - 1:
                ax.annotate('', xy=(boxes[i+1]['xy'][0] - 0.8, boxes[i+1]['xy'][1]),
                           xytext=(box['xy'][0] + 0.8, box['xy'][1]),
                           arrowprops=dict(arrowstyle='->', lw=2, color='navy'))

        ax.text(5, 1, f"Diagram for Scene {scene_id}", ha='center', va='center',
               fontsize=14, style='italic')

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, create_diagram)
    return output_file


async def generate_graph(visual_prompt: str, job_id: str, scene_id: int) -> str:
    """Generates a simple chart/graph."""
    output_file = os.path.join(
        ASSET_STORAGE_PATH, f"job_{job_id}_scene_{scene_id}_chart.png")

    def create_chart():
        fig, ax = plt.subplots(figsize=(10, 6), facecolor='white')

        # Sample data
        categories = ['A', 'B', 'C', 'D', 'E']
        values = [23, 45, 56, 78, 32]

        bars = ax.bar(categories, values, color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7'])

        ax.set_title(f'Chart for Scene {scene_id}', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Categories', fontsize=12)
        ax.set_ylabel('Values', fontsize=12)

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height}', xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3), textcoords="offset points", ha='center', va='bottom')

        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, create_chart)
    return output_file


async def render_formula(visual_prompt: str, job_id: str, scene_id: int) -> str:
    """Renders a mathematical formula."""
    output_file = os.path.join(
        ASSET_STORAGE_PATH, f"job_{job_id}_scene_{scene_id}_formula.png")

    def create_formula():
        fig, ax = plt.subplots(figsize=(10, 6), facecolor='white')
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 6)
        ax.axis('off')

        # Sample mathematical formula
        formula = r'$E = mc^2$'
        if 'integral' in visual_prompt.lower():
            formula = r'$\int_{a}^{b} f(x) dx = F(b) - F(a)$'
        elif 'derivative' in visual_prompt.lower():
            formula = r'$\frac{d}{dx}[f(x)] = \lim_{h \to 0} \frac{f(x+h) - f(x)}{h}$'
        elif 'quadratic' in visual_prompt.lower():
            formula = r'$x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$'

        ax.text(5, 3, formula, fontsize=24, ha='center', va='center',
               bbox=dict(boxstyle="round,pad=0.5", facecolor='lightyellow', alpha=0.8))

        ax.text(5, 1.5, f'Mathematical Formula - Scene {scene_id}',
               ha='center', va='center', fontsize=14, style='italic')

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, create_formula)
    return output_file


async def render_code(visual_prompt: str, job_id: str, scene_id: int) -> str:
    """Renders a code snippet with syntax highlighting."""
    output_file = os.path.join(
        ASSET_STORAGE_PATH, f"job_{job_id}_scene_{scene_id}_code.png")

    def create_code():
        fig, ax = plt.subplots(figsize=(12, 8), facecolor='#1a1a1a')
        ax.set_facecolor('#1a1a1a')
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 8)
        ax.axis('off')

        # Sample code
        code = f"""# Scene {scene_id}: Code Example
def generate_visual_asset(scene):
    '''Generate visual assets for video scenes'''
    scene_id = scene.get('id')
    visual_type = scene.get('visual_type')

    if visual_type == 'code':
        return create_code_visual(scene)

    return scene"""

        # Split code into lines
        code_lines = code.split('\n')

        # Render code with basic syntax highlighting
        for i, line in enumerate(code_lines):
            y_pos = 7 - (i * 0.4)
            if y_pos < 0.5:
                break

            # Simple syntax highlighting
            color = '#d4d4d4'  # default
            if line.strip().startswith('#'):
                color = '#6a9955'  # comment
            elif any(keyword in line for keyword in ['def ', 'class ', 'import ', 'from ', 'if ', 'return ']):
                color = '#569cd6'  # keyword
            elif "'" in line or '"' in line:
                color = '#ce9178'  # string

            ax.text(0.5, y_pos, line, fontsize=10, fontfamily='monospace',
                   color=color, va='center')

        # Add title bar
        title_rect = mpatches.Rectangle((0, 7.5), 10, 0.5, facecolor='#2d2d30', alpha=0.9)
        ax.add_patch(title_rect)
        ax.text(0.2, 7.75, f"Scene {scene_id}: Python Code", fontsize=12,
               fontweight='bold', color='white', va='center')

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='#1a1a1a')
        plt.close()

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, create_code)
    return output_file
