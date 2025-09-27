import io
import logging
import json
from typing import List, Dict
from google import genai

from app.core.config import settings
from app.utils.file import FileContext
logger = logging.getLogger(__name__)

class LLMService:
    """
    LLM service that generates structured video scripts from source text using Google Gemini.
    """

    def __init__(self):
        # self.client = AsyncOpenAI(
        #     base_url=settings.LLM_URL,
        #     api_key=settings.LLM_API_KEY
        # )
        self.client = genai.Client(api_key=settings.LLM_API_KEY)

        self.model = settings.LLM_MODEL

    async def generate_script_from_file(self, file: FileContext) -> List[Dict]:
        """
        Generate a structured video script from source text using LLM asynchronously.

        Args:
            file: The uploaded file containing the source text

        Returns:
            List of scene dictionaries with id, narration_text, visual_type, and visual_prompt
        """
        logger.info("Starting asynchronous LLM script generation", extra={"file": file.filename})

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

            logger.info("Asynchronous LLM script generation completed", extra={
                "scenes_generated": len(script_scenes),
                "visual_types": [scene["visual_type"] for scene in script_scenes]
            })

            return script_scenes

        except Exception as e:
            logger.error("Asynchronous LLM script generation failed", extra={"error": str(e)})
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
            import re
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
        valid_types = ["slide", "diagram", "code", "formula", "chart"]
        visual_type = visual_type.lower().strip()

        if visual_type in valid_types:
            return visual_type

        # Map common variations
        type_mappings = {
            "presentation": "slide",
            "slides": "slide",
            "flowchart": "diagram",
            "graph": "chart",
            "plot": "chart",
            "equation": "formula",
            "math": "formula",
            "programming": "code",
            "algorithm": "code"
        }

        return type_mappings.get(visual_type, "slide")  # Default to slide

    def _generate_fallback_script(self, text: str) -> List[Dict]:
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
                    "visual_prompt": "Create an engaging title slide with the main topic"
                }
            elif i == scene_count - 1:
                # Conclusion scene
                scene = {
                    "id": i + 1,
                    "narration_text": "To summarize, we've covered the essential points and their implications.",
                    "visual_type": "slide",
                    "visual_prompt": "Create a conclusion slide summarizing key takeaways"
                }
            else:
                # Content scenes
                visual_types = ["diagram", "chart", "code", "formula"]
                visual_type = visual_types[(i - 1) % len(visual_types)]

                scene = {
                    "id": i + 1,
                    "narration_text": "Now let's examine this important aspect of our topic in detail.",
                    "visual_type": visual_type,
                    "visual_prompt": f"Create a {visual_type} that illustrates the main concepts"
                }

            fallback_script.append(scene)

        return fallback_script


# Global service instance
llm_service = LLMService()


async def generate_script(file: FileContext) -> List[Dict]:
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
        # Simple test call to verify API connectivity
        # response = await llm_service.client.chat.completions.create(
        #     model=llm_service.model,
        #     messages=[
        #         {"role": "user", "content": "Hello, respond with 'OK' if you're working."}
        #     ],
        #     max_tokens=10,
        #     temperature=0
        # )
        response = llm_service.client.models.generate_content(
            model=llm_service.model,
            contents=[
                "Hello, respond with 'OK' if you're working."
            ],
        )

        # return bool(response.choices and response.choices[0].message.content)
        return bool(response.text)

    except Exception as e:
        logger.error("LLM health check failed", extra={"error": str(e)})
        return False
