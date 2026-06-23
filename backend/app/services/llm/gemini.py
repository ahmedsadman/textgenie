import json
import logging
from decimal import Decimal

from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY
from app.services.llm.base import LLMProvider, MessageParseResult

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model = "gemini-2.5-flash-lite"

    def parse_message(
        self,
        message_content: str,
        sender: str,
        categories: list[str],
        banks: list[str] | None = None,
    ) -> MessageParseResult:
        banks = banks or []
        if not categories and not banks:
            logger.warning(
                "No categories or banks provided — skipping message parsing"
            )
            return MessageParseResult()

        prompt = self.build_message_parse_prompt(
            message_content, sender, categories, banks
        )
        logger.info("Sending message to LLM for parsing")

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        return self._parse_response(response.text, categories, banks)

    def _parse_response(
        self,
        response_text: str | None,
        categories: list[str],
        banks: list[str],
    ) -> MessageParseResult:
        if not response_text:
            logger.error("LLM returned empty response")
            return MessageParseResult()

        data = json.loads(response_text)
        category = _match_category(data.get("category"), categories)
        bank = _match_bank(data.get("bank"), banks)
        balance = _parse_balance(data.get("balance")) if bank else None

        if category:
            logger.info("LLM categorized message as '%s'", category)
        if bank:
            logger.info("LLM identified bank '%s' with balance %s", bank, balance)
        return MessageParseResult(category=category, bank=bank, balance=balance)


def _match_category(raw: str | None, categories: list[str]) -> str | None:
    if not raw:
        return None
    name = raw.strip().lower()
    if not name or name == "uncategorized":
        return None
    for c in categories:
        if c.lower() == name:
            return c
    return None


def _match_bank(raw: str | None, banks: list[str]) -> str | None:
    if not raw:
        return None
    name = raw.strip().lower()
    if not name:
        return None
    for b in banks:
        if b.lower() == name:
            return b
    return None


def _parse_balance(raw: int | float | str | None) -> Decimal | None:
    if raw is None:
        return None
    return Decimal(str(raw))
