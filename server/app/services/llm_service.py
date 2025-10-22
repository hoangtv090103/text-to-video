import asyncio
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
                    content="""You are an expert video script writer and content analyst. Your task is to:

1. ANALYZE the uploaded file content thoroughly
2. IDENTIFY the main topics, concepts, and structure
3. CREATE an appropriate number of video scenes based on content complexity
4. GENERATE detailed visual prompts for each scene

Key principles:
- Content determines scene count
- Each scene should cover a logical unit of information
- Visual prompts must be extremely detailed and specific
- Narration should be engaging and educational
- Maintain content accuracy and completeness"""
                ),
                HumanMessage(
                    content=f"Content from file '{file.filename}':\n\n{text_content[:8000]}\n\n{prompt}"
                ),
            ]

            # Retry logic with exponential backoff
            max_retries = 3
            retry_delay = 2  # seconds
            script_content = ""  # Initialize to avoid unbound variable

            for attempt in range(max_retries):
                try:
                    logger.info(
                        "Calling LLM API",
                        extra={
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "provider": self.provider
                        }
                    )

                    # Generate response using LangChain
                    response = await self.llm.ainvoke(messages)

                    # Extract content from response
                    script_content = response.content if hasattr(response, "content") else str(response)

                    # Debug logging for empty responses
                    if not script_content or len(script_content.strip()) == 0:
                        error_msg = f"LLM returned empty response on attempt {attempt + 1}"
                        logger.warning(
                            error_msg,
                            extra={
                                "provider": self.provider,
                                "response_type": type(response).__name__,
                                "has_content_attr": hasattr(response, "content"),
                                "attempt": attempt + 1
                            }
                        )

                        # Retry if not last attempt
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)
                            logger.info(f"Retrying in {wait_time} seconds...")
                            await asyncio.sleep(wait_time)
                            continue

                        raise ValueError("LLM returned empty response after all retries")

                    logger.debug(
                        "LLM response received successfully",
                        extra={
                            "provider": self.provider,
                            "response_length": len(script_content),
                            "response_preview": script_content[:200],
                            "attempt": attempt + 1
                        }
                    )

                    # Success - break out of retry loop
                    break

                except ValueError as ve:
                    # ValueError is for empty response - we want to retry
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        logger.warning(f"Attempt {attempt + 1} failed: {ve}. Retrying in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                    else:
                        raise
                except Exception as api_error:
                    # Other errors (network, API errors) - retry
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        logger.warning(
                            f"LLM API error on attempt {attempt + 1}: {api_error}. Retrying in {wait_time} seconds..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        raise

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
TASK: Analyze the uploaded file "{file.filename}" and create a comprehensive video script.

ANALYSIS STEPS:
1. Read and understand the complete content
2. Identify main topics, sections, and key concepts
3. Determine logical flow and information hierarchy
4. Decide appropriate number of scenes based on content complexity
5. Create detailed visual representations for each scene

SCENE COUNT GUIDELINES:
- Simple content (1-2 main topics): 3-4 scenes
- Medium complexity (3-5 main topics): 5-8 scenes
- Complex content (6+ topics, technical details): 8-12 scenes
- Academic/research papers: 10-15 scenes
- Tutorials/how-to guides: 6-10 scenes
- Business presentations: 5-8 scenes

CRITICAL: You MUST respond ONLY with valid JSON. No explanations, no markdown, no additional text.

Required JSON structure:
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

Requirements:
- Scene count: Based on content complexity (see guidelines above)
- Each scene narration: 20-40 seconds when spoken
- Visual types: slide, diagram, chart, formula, or code
- EXTREMELY detailed visual prompts (minimum 80 words per prompt)
- Cover ALL important content from the file
- Maintain logical progression and flow

RESPONSE FORMAT - YOU MUST FOLLOW THIS EXACTLY:
1. Start your response with ```json
2. Then the JSON array
3. End with ```
4. NO other text before or after

Example response:
```json
[
    {{
        "id": 1,
        "narration_text": "Welcome to our exploration of machine learning...",
        "visual_type": "slide",
        "visual_prompt": "Title: Introduction to Machine Learning\\nKey Points:\\n- Definition and core concepts\\n- Real-world applications\\n- Benefits and challenges\\nVisual style: Modern, tech-themed with icons"
    }}
]
```

CONTENT ANALYSIS REQUIREMENTS:
- Extract ALL key information from the file
- Identify main themes, subtopics, and supporting details
- Note any data, statistics, examples, or case studies
- Recognize technical terms, definitions, and concepts
- Understand the document's structure and organization

VISUAL PROMPT GUIDELINES (VERY IMPORTANT):

For "slide":
- Start with a clear, concise title (max 12 words)
- Include 4-6 key bullet points with specific details
- Mention desired visual elements (icons, images, shapes, colors)
- Specify layout preference (centered, left-aligned, etc.)
- Include any relevant data, statistics, or examples from the content
- Example: "Title: Introduction to Machine Learning\\n\\nKey Points:\\n- Definition: Systems that learn from data without explicit programming\\n- Applications: Image recognition (95% accuracy), natural language processing, recommendation systems\\n- Benefits: Automation, pattern discovery, predictive analytics\\n- Challenges: Data quality requirements, computational resources\\n- Real-world impact: Used by Netflix, Google, Amazon for personalization\\n\\nVisual style: Professional, clean layout with tech-themed icons, blue gradient background"

For "diagram":
- Specify diagram type (flowchart, process flow, organizational chart, mind map, etc.)
- List all nodes/boxes with their labels and descriptions
- Describe connections and flow direction
- Include any decision points or branching logic
- Use actual data/processes from the content
- Example: "Flowchart showing machine learning workflow:\\n1. Data Collection (rectangle, top) - Gather raw data from various sources\\n2. Data Preprocessing (rectangle, arrow down) - Clean, normalize, and prepare data\\n3. Model Training (rectangle, arrow down) - Train algorithm on prepared dataset\\n4. Evaluation (diamond, decision point) - Test model performance\\n5. If accuracy > 90%: Deploy (rectangle, arrow right) - Release to production\\n6. Else: Tune Hyperparameters (rectangle, arrow back to step 3) - Adjust parameters\\nUse blue boxes, green for success, yellow for decision points, include data flow arrows"

For "chart":
- Specify chart type (bar, line, pie, scatter, area, etc.)
- Use actual data from the content when available
- Label axes clearly with units
- Include title and legend descriptions
- Suggest color scheme and styling
- Add data source or context if mentioned in content
- Example: "Bar chart comparing ML algorithm performance:\\nTitle: 'Model Accuracy Comparison (2023 Study)'\\nX-axis: Algorithm names (Linear Regression, Decision Tree, Random Forest, Neural Network)\\nY-axis: Accuracy (0-100%)\\nData: 72%, 85%, 92%, 94%\\nColors: Professional gradient from blue to green\\nInclude value labels on top of each bar, add subtle grid lines\\nSource: Based on 10,000 test samples from UCI Machine Learning Repository"

For "formula":
- Write the mathematical equation clearly using proper notation
- Include variable definitions and units
- Provide context for what the formula represents
- Specify notation style (LaTeX preferred)
- Include any assumptions or conditions mentioned in content
- Example: "Linear Regression Formula:\\n\\ny = mx + b\\n\\nWhere:\\n- y: predicted output value (dependent variable)\\n- m: slope (weight/coefficient) - rate of change\\n- x: input feature (independent variable)\\n- b: y-intercept (bias) - baseline value\\n\\nRepresents: The fundamental equation for linear regression prediction\\nAssumptions: Linear relationship, independent observations, normal distribution\\nDisplay style: Large, centered equation with clear variable labels, use LaTeX formatting"

For "code":
- Specify programming language and framework
- Provide actual working code example from content or create relevant example
- Include detailed comments explaining key parts
- Mention syntax highlighting preferences and theme
- Keep code concise (10-25 lines maximum)
- Include any imports, dependencies, or setup requirements
- Example: "Python code for linear regression using scikit-learn:\\n```python\\n# Import required libraries\\nfrom sklearn.linear_model import LinearRegression\\nfrom sklearn.model_selection import train_test_split\\nimport numpy as np\\nimport matplotlib.pyplot as plt\\n\\n# Create sample dataset\\nX = np.array([[1], [2], [3], [4], [5]]).reshape(-1, 1)\\ny = np.array([2, 4, 5, 4, 5])\\n\\n# Split data for training and testing\\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\\n\\n# Initialize and train the model\\nmodel = LinearRegression()\\nmodel.fit(X_train, y_train)\\n\\n# Make predictions\\nprediction = model.predict([[6]])\\nprint(f'Predicted value: {{prediction[0]:.2f}}')\\n```\\nUse syntax highlighting with dark background (VS Code Dark+ theme), highlight key functions in blue"

CONTENT COVERAGE REQUIREMENTS:
- Ensure ALL major topics from the file are covered
- Include important details, examples, and case studies
- Maintain the original document's structure and flow
- Don't skip technical details or important nuances
- Preserve key statistics, data points, and references

QUALITY CHECKLIST:
- Each scene has a clear purpose and logical progression
- Visual prompts are extremely detailed (80+ words minimum)
- Narration is engaging and educational
- All important content is represented
- Scene count matches content complexity
- No information is lost or oversimplified

REMEMBER: The quality of the visual output directly depends on how detailed and specific your visual_prompt is. Be as descriptive as possible and ensure complete content coverage!
"""

    def _parse_script_response(self, response_content: str) -> list[dict]:
        """
        Parse the LLM response to extract structured script data.

        Args:
            response_content: Raw response from LLM

        Returns:
            List of scene dictionaries
        """
        # Initialize json_content outside try block to avoid unbound variable in except
        json_content = ""

        try:
            # Check if response is empty
            if not response_content or len(response_content.strip()) == 0:
                raise ValueError("Response content is empty")

            # Log full response for debugging
            logger.debug(
                "Parsing LLM response",
                extra={
                    "response_length": len(response_content),
                    "starts_with": response_content[:50],
                    "ends_with": response_content[-50:] if len(response_content) > 50 else response_content
                }
            )

            # Try to extract JSON from the response
            import re

            # Pattern 1: JSON in code blocks (use greedy match)
            json_match = re.search(r"```json\s*(.*)\s*```", response_content, re.DOTALL | re.IGNORECASE)
            if json_match:
                json_content = json_match.group(1).strip()
                logger.debug(f"Found JSON in code block (length: {len(json_content)})")

            # Pattern 2: JSON in any code block (use greedy match)
            if not json_content:
                json_match = re.search(r"```\s*(.*)\s*```", response_content, re.DOTALL)
                if json_match:
                    potential_json = json_match.group(1).strip()
                    if potential_json.startswith('[') or potential_json.startswith('{'):
                        json_content = potential_json
                        logger.debug(f"Found JSON in generic code block (length: {len(json_content)})")

            # Pattern 3: Raw JSON array (greedy to capture all objects)
            if not json_content:
                # Use greedy match to capture entire array with all objects
                json_match = re.search(r"\[\s*\{.*\}\s*\]", response_content, re.DOTALL)
                if json_match:
                    json_content = json_match.group(0)
                    logger.debug(f"Found raw JSON array (length: {len(json_content)})")

            # Pattern 4: Try entire response if it looks like JSON
            if not json_content:
                stripped = response_content.strip()
                if stripped.startswith('[') or stripped.startswith('{'):
                    json_content = stripped
                    logger.debug("Using entire response as JSON")

            if not json_content:
                logger.error(
                    "No JSON pattern matched",
                    extra={
                        "response_length": len(response_content),
                        "response_preview": response_content[:1000],
                        "has_json_marker": "```json" in response_content.lower(),
                        "has_code_block": "```" in response_content
                    }
                )
                raise ValueError(f"No JSON found in response. Response preview: {response_content[:300]}")

            # Parse the JSON
            logger.debug(f"Attempting to parse JSON (length: {len(json_content)})")
            script_data = json.loads(json_content)

            # Handle if response is a dict instead of list
            if isinstance(script_data, dict):
                if "scenes" in script_data:
                    script_data = script_data["scenes"]
                elif "script" in script_data:
                    script_data = script_data["script"]
                else:
                    # Convert single scene dict to list
                    script_data = [script_data]

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
                else:
                    logger.warning(
                        f"Skipping scene {i+1} due to missing required fields",
                        extra={
                            "has_narration": bool(validated_scene["narration_text"]),
                            "has_prompt": bool(validated_scene["visual_prompt"])
                        }
                    )

            if not validated_scenes:
                raise ValueError("No valid scenes found in parsed response")

            logger.info(f"Successfully parsed {len(validated_scenes)} scenes from LLM response")
            return validated_scenes

        except json.JSONDecodeError as e:
            logger.error(
                "JSON decode error",
                extra={
                    "error": str(e),
                    "json_content": json_content[:500] if json_content else "None",
                    "response_preview": response_content[:500]
                },
            )
            raise ValueError(f"Invalid JSON format: {str(e)}") from e
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
