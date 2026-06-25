import json
import logging
import time
from decimal import Decimal

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.config import GEMINI_API_KEY
from app.services.llm.base import LLMProvider, MessageParseResult, ParsePrompt

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_RETRYABLE_NETWORK_ERRORS = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.RemoteProtocolError,
    TimeoutError,
)


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, genai_errors.APIError):
        return exc.code in _RETRYABLE_STATUS_CODES
    return isinstance(exc, _RETRYABLE_NETWORK_ERRORS)


class GeminiProvider(LLMProvider):
    MODELS = ("gemini-2.5-flash-lite", "gemini-3.1-flash-lite")
    MAX_CYCLES = 3
    BACKOFF_BASE_SECONDS = 10.0

    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def parse_message(
        self,
        message_content: str,
        sender: str,
        categories: list[str],
        banks: list[str] | None = None,
    ) -> MessageParseResult:
        banks = banks or []
        if not categories and not banks:
            logger.warning("No categories or banks provided — skipping message parsing")
            return MessageParseResult()

        prompt = self.build_message_parse_prompt(
            message_content, sender, categories, banks
        )

        response_text = self._generate_with_fallback(prompt)
        return self._parse_response(response_text, categories, banks)

    def _generate_with_fallback(self, prompt: ParsePrompt) -> str | None:
        last_exc: BaseException | None = None
        for cycle in range(self.MAX_CYCLES):
            for model in self.MODELS:
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=prompt.contents,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            system_instruction=prompt.system_instruction,
                        ),
                    )
                    usage = response.usage_metadata
                    logger.info(
                        "LLM response: model=%s, input_tokens=%s, cached_tokens=%s, output_tokens=%s",
                        model,
                        usage.prompt_token_count,
                        usage.cached_content_token_count,
                        usage.candidates_token_count,
                    )
                    return response.text
                except Exception as exc:
                    if not _is_retryable(exc):
                        raise
                    last_exc = exc
                    logger.warning(
                        "Gemini call failed (model=%s, cycle=%d/%d): %s",
                        model,
                        cycle + 1,
                        self.MAX_CYCLES,
                        exc,
                    )

            if cycle < self.MAX_CYCLES - 1:
                delay = self.BACKOFF_BASE_SECONDS * (2**cycle)
                logger.warning(
                    "All Gemini models failed on cycle %d/%d; backing off %.2fs",
                    cycle + 1,
                    self.MAX_CYCLES,
                    delay,
                )
                time.sleep(delay)

        logger.error(
            "Gemini retry exhausted after %d cycles; last error: %s",
            self.MAX_CYCLES,
            last_exc,
        )
        assert last_exc is not None
        raise last_exc

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
