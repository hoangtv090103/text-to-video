import json
import logging

from app.core.config import settings
from app.core.llm_factory import llm_factory
from app.utils.file import FileContext

logger = logging.getLogger(__name__)


class LLMService:
    """
    LLM service that generates structured video scripts from source text using configurable LLM providers.
    """

    def __init__(self):
        self.llm = llm_factory.get_llm()
        self.provider = settings.LLM_PROVIDER

    async def generate_script_from_file(self, file: FileContext) -> list[dict]:
        """
        Generate a structured video script from source text using LLM asynchronously.

        Args:
            file: The uploaded file containing the source text

        Returns:
            List of scene dictionaries with id, narration_text, visual_type, and visual_prompt
        """
        logger.info(
            "Starting asynchronous LLM script generation",
            extra={"uploaded_file": file.filename, "provider": self.provider},
        )

        # Validate file contents
        if not file or not file.contents:
            raise ValueError("File contents are empty or invalid")

        # Check cache first
        from app.utils.cache import get_from_cache, set_cache
        content_key = file.contents.decode('utf-8', errors='ignore')[:1000]  # Use first 1KB as key
        cached_result = await get_from_cache("llm", content_key)
        if cached_result:
            logger.info("Using cached LLM result", extra={"uploaded_file": file.filename})
            return cached_result

        try:
            # Extract text content from file
            text_content = self._extract_text_from_file(file)

            # Create the prompt for script generation
            prompt = self._create_script_prompt(file)

            # Use LangChain with proper Message objects
            from langchain_core.messages import HumanMessage, SystemMessage

            messages = [
                SystemMessage(
                    content="You are an expert at creating engaging video scripts from text content. "
                ),
                HumanMessage(
                    content=f"Content from file '{file.filename}':\n\n{text_content[:8000]}\n\n{prompt}"
                ),
            ]

            # Generate response using LangChain
            response = await self.llm.ainvoke(messages)

            # Extract content from response
            script_content = response.content if hasattr(response, "content") else str(response)

            script_scenes = self._parse_script_response(script_content)

            logger.info(
                "Asynchronous LLM script generation completed",
                extra={
                    "scenes_generated": len(script_scenes),
                    "visual_types": [scene["visual_type"] for scene in script_scenes],
                    "provider": self.provider,
                },
            )

            # Cache the successful result
            await set_cache("llm", content_key, script_scenes)
            return script_scenes

        except Exception as e:
            logger.error(
                "Asynchronous LLM script generation failed",
                extra={"error": str(e), "provider": self.provider},
            )
            # Fallback to mock script on failure
            return self._generate_fallback_script(file.contents)

    def _extract_text_from_file(self, file: FileContext) -> str:
        """
        Extract text content from uploaded file.

        Args:
            file: FileContext containing file contents and metadata

        Returns:
            Extracted text content as string
        """
        try:
            # Use the text extractor utility for proper PDF handling
            if file.filename.lower().endswith(".pdf"):
                from app.utils.text_extractor import extract_text_from_pdf_bytes

                logger.info("Extracting text from PDF", extra={"uploaded_file": file.filename})
                return extract_text_from_pdf_bytes(file.contents, max_chars=8000)

            # For text-based files, decode as UTF-8
            text_content = file.contents.decode("utf-8", errors="ignore")
            return text_content[:8000]  # Limit to avoid token limits

        except Exception as e:
            logger.error(
                "Failed to extract text from file",
                extra={"error": str(e), "uploaded_file": file.filename},
            )
            return "Unable to extract text content from file."

    def _create_script_prompt(self, file: FileContext) -> str:
        """
        Create a detailed prompt for the LLM to generate video script.

        Args:
            file: The uploaded file context

        Returns:
            Formatted prompt string
        """
        return f"""
Based on the content of the uploaded file "{file.filename}", create a structured video script that breaks down the content into engaging scenes.

For each scene, provide:
1. A clear, conversational narration text that explains the key concepts
2. A visual type from the supported list
3. A detailed visual prompt describing what should be shown

Requirements:
- Create 3-7 scenes maximum
- Each scene should be 20-40 seconds of narration
- Use simple, clear language suitable for educational content
- Ensure visual prompts are specific and actionable
- Focus on the most important concepts from the source material

Return the response as a JSON array with this exact structure:
```json
[
    {{
        "id": 1,
        "narration_text": "Clear, engaging narration explaining the concept...",
        "visual_type": "slide",
        "visual_prompt": "Detailed description of what should be visualized..."
    }}
]
```

Visual types must be one of: slide, diagram, chart, formula, code
- Use "slide" for presentation slides, images, or animations
- Use "diagram" for flowcharts, process diagrams, or concept maps
- Use "chart" for graphs, plots, or data visualizations
- Use "formula" for mathematical equations
- Use "code" for programming examples or algorithms
"""

    def _parse_script_response(self, response_content: str) -> list[dict]:
        """
        Parse the LLM response to extract structured script data.

        Args:
            response_content: Raw response from LLM

        Returns:
            List of scene dictionaries
        """
        try:
            # Try to extract JSON from the response
            # Look for JSON blocks in the response
            import re

            json_match = re.search(r"```json\s*(.*?)\s*```", response_content, re.DOTALL)
            if json_match:
                json_content = json_match.group(1)
            else:
                # Try to find JSON without code blocks
                json_match = re.search(r"\[.*\]", response_content, re.DOTALL)
                if json_match:
                    json_content = json_match.group(0)
                else:
                    raise ValueError("No JSON found in response")

            # Parse the JSON
            script_data = json.loads(json_content)

            # Validate and clean the data
            validated_scenes = []
            for i, scene in enumerate(script_data):
                validated_scene = {
                    "id": scene.get("id", i + 1),
                    "narration_text": scene.get("narration_text", "").strip(),
                    "visual_type": self._validate_visual_type(scene.get("visual_type", "slide")),
                    "visual_prompt": scene.get("visual_prompt", "").strip(),
                }

                # Ensure all required fields are present
                if validated_scene["narration_text"] and validated_scene["visual_prompt"]:
                    validated_scenes.append(validated_scene)

            if not validated_scenes:
                raise ValueError("No valid scenes found in parsed response")

            return validated_scenes

        except Exception as e:
            logger.error(
                "Failed to parse LLM response",
                extra={"error": str(e), "response": response_content[:500]},
            )
            raise

    def _validate_visual_type(self, visual_type: str) -> str:
        """
        Validate and normalize visual type to match asset router handlers.

        Args:
            visual_type: Raw visual type from LLM

        Returns:
            Validated visual type that the router can handle
        """
        valid_types = [
            "slide",
            "diagram",
            "chart",
            "graph",
            "formula",
            "code",
            "image",
            "animation",
        ]
        visual_type_cleaned = (visual_type or "").lower().strip()

        if visual_type_cleaned in valid_types:
            # Map graph to chart (router uses both)
            if visual_type_cleaned == "graph":
                return "chart"
            # Map image and animation to slide (router handles as presentation)
            if visual_type_cleaned in {"image", "animation"}:
                return "slide"
            return visual_type_cleaned

        # Map common variations
        type_mappings = {
            "presentation": "slide",
            "slides": "slide",
            "picture": "slide",
            "flowchart": "diagram",
            "plot": "chart",
            "equation": "formula",
            "math": "formula",
            "programming": "code",
            "algorithm": "code",
        }

        return type_mappings.get(visual_type_cleaned, "slide")

    def _generate_fallback_script(self, text: str) -> list[dict]:
        """
        Generate a fallback script when LLM fails.

        Args:
            text: Source text

        Returns:
            Basic script structure
        """
        logger.warning("Using fallback script generation")

        # Create a simple script based on text length
        word_count = len(text.split())
        scene_count = max(3, min(7, word_count // 50))  # 1 scene per ~50 words

        fallback_script = []

        for i in range(scene_count):
            if i == 0:
                # Introduction scene
                scene = {
                    "id": i + 1,
                    "narration_text": "Welcome to this presentation. Let's explore the key concepts and ideas.",
                    "visual_type": "slide",
                    "visual_prompt": "Create an engaging title slide with the main topic",
                }
            elif i == scene_count - 1:
                # Conclusion scene
                scene = {
                    "id": i + 1,
                    "narration_text": "To summarize, we've covered the essential points and their implications.",
                    "visual_type": "slide",
                    "visual_prompt": "Create a conclusion slide summarizing key takeaways",
                }
            else:
                # Content scenes
                visual_types = ["diagram", "chart", "code", "formula"]
                visual_type = visual_types[(i - 1) % len(visual_types)]

                scene = {
                    "id": i + 1,
                    "narration_text": "Now let's examine this important aspect of our topic in detail.",
                    "visual_type": visual_type,
                    "visual_prompt": f"Create a {visual_type} that illustrates the main concepts",
                }

            fallback_script.append(scene)

        return fallback_script

# Global service instance
llm_service = LLMService()


async def generate_script(file: FileContext) -> list[dict]:
    """
    Main function to generate script from text.

    Args:
        text: The source text to convert into a video script

    Returns:
        List of scene dictionaries with id, narration_text, visual_type, and visual_prompt
    """
    return await llm_service.generate_script_from_file(file)


# Health check function for the LLM service
async def check_llm_health() -> bool:
    """
    Check if the LLM service is healthy and responsive.

    Returns:
        True if the service is healthy, False otherwise
    """
    try:
        from langchain_core.messages import HumanMessage

        # Simple test call to verify LLM connectivity
        messages = [HumanMessage(content="Hello, respond with 'OK' if you're working.")]

        response = await llm_service.llm.ainvoke(messages)

        # Check if we got a valid response
        content = response.content if hasattr(response, "content") else str(response)
        return bool(content and len(content.strip()) > 0)

    except Exception as e:
        logger.error(
            "LLM health check failed", extra={"error": str(e), "provider": llm_service.provider}
        )
        return False
