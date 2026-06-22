import json
import logging

from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY
from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model = "gemini-2.5-flash"

    def categorize_message(
        self, message_content: str, sender: str, categories: list[str]
    ) -> str | None:
        if not categories:
            return None

        prompt = self.build_categorization_prompt(
            message_content, sender, categories
        )
        logger.info("Sending message to LLM for categorization")

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        return self._parse_response(response.text, categories)

    def _parse_response(
        self, response_text: str | None, categories: list[str]
    ) -> str | None:
        if not response_text:
            logger.error("LLM returned empty response")
            return None

        try:
            result = json.loads(response_text)
            category = result.get("category", "").strip().lower()
            categories_lower = {c.lower(): c for c in categories}
            if category in categories_lower:
                matched = categories_lower[category]
                logger.info("LLM categorized message as '%s'", matched)
                return matched
            logger.info("LLM returned uncategorized")
            return None
        except (json.JSONDecodeError, AttributeError):
            logger.error("Failed to parse LLM response: %s", response_text)
            return None
