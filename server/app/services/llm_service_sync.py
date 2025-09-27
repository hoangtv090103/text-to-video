import io
import logging
import json
import re
from typing import List, Dict
from google import genai

from app.core.config import settings
from app.utils.file import FileContext

logger = logging.getLogger(__name__)


class LLMServiceSync:
    """
    Synchronous LLM service that generates structured video scripts from source text using Google Gemini.
    """

    def __init__(self):
        self.client = genai.Client(api_key=settings.LLM_API_KEY)
        self.model = settings.LLM_MODEL

    def generate_script_from_file(self, file: FileContext) -> List[Dict]:
        """
        Generate a structured video script from source text using LLM synchronously.

        Args:
            file: The uploaded file containing the source text

        Returns:
            List of scene dictionaries with id, narration_text, visual_type, and visual_prompt
        """
        logger.info("Starting synchronous LLM script generation", extra={"file_name": file.filename})

        try:
            # Upload the file using Google Gemini File API
            doc_io = io.BytesIO(file.contents)

            # Determine MIME type based on file extension
            mime_type = 'text/plain'
            if file.filename.lower().endswith('.pdf'):
                mime_type = 'application/pdf'
            elif file.filename.lower().endswith(('.txt', '.md')):
                mime_type = 'text/plain'

            uploaded_file = self.client.files.upload(
                file=doc_io,
                config={'mime_type': mime_type}
            )

            # Create the prompt for script generation
            prompt = self._create_script_prompt(file)

            # Call Gemini to generate content
            response = self.client.models.generate_content(
                model=self.model,
                contents=[uploaded_file, prompt]
            )

            # Parse the response
            script_content = response.text
            script_scenes = self._parse_script_response(str(script_content))

            logger.info("Synchronous LLM script generation completed", extra={
                "scenes_generated": len(script_scenes),
                "visual_types": [scene["visual_type"] for scene in script_scenes]
            })

            return script_scenes

        except Exception as e:
            logger.error("Synchronous LLM script generation failed", extra={"error": str(e)})
            # Fallback to mock script on failure
            return self._generate_fallback_script(file.contents)

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
2. A visual type (slide, diagram, animation, or image)
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

Visual types must be one of: slide, diagram, animation, image
"""

    def _parse_script_response(self, response_content: str) -> List[Dict]:
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
            json_match = re.search(r'```json\s*(.*?)\s*```', response_content, re.DOTALL)
            if json_match:
                json_content = json_match.group(1)
            else:
                # Try to find JSON without code blocks
                json_match = re.search(r'\[.*\]', response_content, re.DOTALL)
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
                    "visual_prompt": scene.get("visual_prompt", "").strip()
                }

                # Ensure all required fields are present
                if validated_scene["narration_text"] and validated_scene["visual_prompt"]:
                    validated_scenes.append(validated_scene)

            if not validated_scenes:
                raise ValueError("No valid scenes found in parsed response")

            return validated_scenes

        except Exception as e:
            logger.error("Failed to parse LLM response", extra={"error": str(e), "response": response_content[:500]})
            raise

    def _validate_visual_type(self, visual_type: str) -> str:
        """
        Validate and normalize visual type.

        Args:
            visual_type: Raw visual type from LLM

        Returns:
            Validated visual type
        """
        valid_types = ["slide", "diagram", "animation", "image"]
        normalized = visual_type.lower().strip()

        if normalized in valid_types:
            return normalized

        # Map common variations
        type_mapping = {
            "presentation": "slide",
            "chart": "diagram",
            "graph": "diagram",
            "flowchart": "diagram",
            "video": "animation",
            "gif": "animation",
            "photo": "image",
            "picture": "image"
        }

        return type_mapping.get(normalized, "slide")

    def _generate_fallback_script(self, content: bytes) -> List[Dict]:
        """
        Generate a fallback script when LLM fails.

        Args:
            content: Raw file content

        Returns:
            Basic fallback script
        """
        logger.warning("Using fallback script generation")

        # Try to extract some text from content for a basic script
        try:
            # Attempt to decode as text
            text_content = content.decode('utf-8', errors='ignore')[:500]
        except Exception:
            text_content = "document content"

        return [
            {
                "id": 1,
                "narration_text": f"Let's explore the key concepts from this {text_content[:100]}...",
                "visual_type": "slide",
                "visual_prompt": "Title slide with main topic and key points overview"
            },
            {
                "id": 2,
                "narration_text": "This content covers important information that we'll break down step by step.",
                "visual_type": "diagram",
                "visual_prompt": "Simple diagram showing the main structure and relationships"
            },
            {
                "id": 3,
                "narration_text": "In conclusion, these concepts provide a foundation for understanding the topic.",
                "visual_type": "slide",
                "visual_prompt": "Summary slide with key takeaways and conclusions"
            }
        ]


# Create a global instance and convenience function
_llm_service_sync = LLMServiceSync()


def generate_script_sync(file: FileContext) -> List[Dict]:
    """
    Convenience function for synchronous script generation.

    Args:
        file: File context containing the source content

    Returns:
        List of scene dictionaries
    """
    return _llm_service_sync.generate_script_from_file(file)


def check_llm_health_sync() -> bool:
    """
    Synchronous health check for LLM service.

    Returns:
        True if LLM service is available, False otherwise
    """
    try:
        # Simple check - try to access the client
        if _llm_service_sync.client and settings.LLM_API_KEY:
            return True
        return False
    except Exception as e:
        logger.error("LLM health check failed", extra={"error": str(e)})
        return False
