import json
import logging
import time
from decimal import Decimal
from typing import get_args

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.config import GEMINI_API_KEY
from app.constants import TransactionType
from app.services.llm.base import (
    BillMetadataResult,
    LLMProvider,
    MetadataResult,
    ParsePrompt,
)

_VALID_TRANSACTION_TYPES = frozenset(get_args(TransactionType))

logger = logging.getLogger(__name__)

# --- Helpers ---

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


_model_counts: dict[str, int] = {}
_total_requests = 0
_STATS_INTERVAL = 10


def _track_model_usage(model: str) -> None:
    global _total_requests
    _total_requests += 1
    _model_counts[model] = _model_counts.get(model, 0) + 1
    if _total_requests % _STATS_INTERVAL == 0:
        parts = [
            f"{m}={c / _total_requests:.1%}" for m, c in sorted(_model_counts.items())
        ]
        logger.info(
            "LLM model stats (total=%d): %s",
            _total_requests,
            ", ".join(parts),
        )


def _match_name(raw: str | None, candidates: list[str]) -> str | None:
    if not raw:
        return None
    name = raw.strip().lower()
    if not name or name == "uncategorized":
        return None
    for c in candidates:
        if c.lower() == name:
            return c
    return None


def _parse_balance(raw: int | float | str | None) -> Decimal | None:
    if raw is None:
        return None
    return Decimal(str(raw))


def _parse_transaction_type(raw: str | None) -> str | None:
    if not isinstance(raw, str):
        return None
    value = raw.strip().lower()
    return value if value in _VALID_TRANSACTION_TYPES else None


def _parse_currency(raw: str | None) -> str | None:
    if not isinstance(raw, str):
        return None
    value = raw.strip().upper()
    return value if len(value) == 3 and value.isalpha() else None


def _parse_month(raw) -> int | None:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if 1 <= value <= 12 else None


def _parse_year(raw) -> int | None:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if 2000 <= value <= 2100 else None


class GeminiProvider(LLMProvider):
    MODELS = ("gemini-2.5-flash-lite", "gemini-3.1-flash-lite")
    MAX_CYCLES = 3
    BACKOFF_BASE_SECONDS = 10.0

    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def categorize(
        self, content: str, sender: str, categories: list[str]
    ) -> str | None:
        if not categories:
            return None
        prompt = self.build_categorize_prompt(content, sender, categories)
        response_text = self._generate_with_fallback(prompt)
        return self._parse_categorize_response(response_text, categories)

    def extract_metadata(
        self,
        content: str,
        sender: str,
        banks: list[str],
        normalized_currency: str,
    ) -> MetadataResult:
        if not banks:
            return MetadataResult()
        prompt = self.build_metadata_prompt(content, sender, banks, normalized_currency)
        response_text = self._generate_with_fallback(prompt)
        return self._parse_metadata_response(response_text, banks)

    def extract_bill_metadata(
        self,
        content: str,
        sender: str,
        banks: list[str],
        normalized_currency: str,
    ) -> BillMetadataResult:
        prompt = self.build_bill_prompt(content, sender, banks, normalized_currency)
        response_text = self._generate_with_fallback(prompt)
        return self._parse_bill_response(response_text, banks)

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
                        "LLM response: model=%s, input=%s, cached=%s, output=%s",
                        model,
                        usage.prompt_token_count,
                        usage.cached_content_token_count,
                        usage.candidates_token_count,
                    )
                    _track_model_usage(model)
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

    def _parse_categorize_response(
        self, response_text: str | None, categories: list[str]
    ) -> str | None:
        if not response_text:
            logger.error("LLM returned empty categorize response")
            return None
        data = json.loads(response_text)
        category = _match_name(data.get("category"), categories)
        if category:
            logger.info("LLM categorized message as '%s'", category)
        return category

    def _parse_metadata_response(
        self, response_text: str | None, banks: list[str]
    ) -> MetadataResult:
        if not response_text:
            logger.error("LLM returned empty metadata response")
            return MetadataResult()
        data = json.loads(response_text)
        bank = _match_name(data.get("bank"), banks)
        balance = _parse_balance(data.get("balance")) if bank else None
        amount = _parse_balance(data.get("amount")) if bank else None
        original_amount = _parse_balance(data.get("original_amount")) if bank else None
        transaction_type = (
            _parse_transaction_type(data.get("transaction_type")) if bank else None
        )
        original_currency = _parse_currency(data.get("original_currency"))

        # amount / original_amount / transaction_type must all three be present
        # to be usable — mirror the "amount and transaction_type paired" rule.
        if amount is None or transaction_type is None:
            amount = None
            original_amount = None
            transaction_type = None

        # original_currency is only meaningful alongside an amount or balance.
        if amount is None and balance is None:
            original_currency = None

        if bank:
            logger.info(
                "LLM identified bank '%s' with balance %s, amount %s, "
                "original_amount %s, type %s, original_currency %s",
                bank,
                balance,
                amount,
                original_amount,
                transaction_type,
                original_currency,
            )
        return MetadataResult(
            bank=bank,
            balance=balance,
            amount=amount,
            transaction_type=transaction_type,
            original_currency=original_currency,
            original_amount=original_amount,
        )

    def _parse_bill_response(
        self, response_text: str | None, banks: list[str]
    ) -> BillMetadataResult:
        if not response_text:
            logger.error("LLM returned empty bill response")
            return BillMetadataResult()
        data = json.loads(response_text)
        bank = _match_name(data.get("bank"), banks)
        normalized_total_due = _parse_balance(data.get("normalized_total_due"))
        original_amount = _parse_balance(data.get("original_amount"))
        original_currency = _parse_currency(data.get("original_currency"))
        statement_month = _parse_month(data.get("statement_month"))
        statement_year = _parse_year(data.get("statement_year"))

        # normalized_total_due / original_amount / original_currency must all be present
        # together to be usable (mirrors the metadata amount rule).
        if (
            normalized_total_due is None
            or original_amount is None
            or original_currency is None
        ):
            normalized_total_due = None
            original_amount = None
            original_currency = None

        logger.info(
            "LLM extracted bill: bank=%s, normalized_total_due=%s, "
            "original_amount=%s, original_currency=%s, "
            "statement_month=%s, statement_year=%s",
            bank,
            normalized_total_due,
            original_amount,
            original_currency,
            statement_month,
            statement_year,
        )
        return BillMetadataResult(
            bank=bank,
            normalized_total_due=normalized_total_due,
            original_amount=original_amount,
            original_currency=original_currency,
            statement_month=statement_month,
            statement_year=statement_year,
        )
