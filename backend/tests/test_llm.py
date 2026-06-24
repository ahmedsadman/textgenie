from decimal import Decimal
from unittest.mock import MagicMock, patch

import httpx
import pytest
from google.genai import errors as genai_errors

from app.services.llm.base import LLMProvider, MessageParseResult
from app.services.llm.gemini import GeminiProvider


class _ConcreteProvider(LLMProvider):
    def parse_message(self, *a, **k):  # pragma: no cover - prompt-builder tests only
        raise NotImplementedError


def _make_response(text):
    response = MagicMock()
    response.text = text
    return response


def _api_error(code, message="boom"):
    return genai_errors.APIError(code, {"error": {"message": message, "status": code}})


@pytest.fixture
def make_provider():
    def _make(response_text=None, side_effect=None):
        with (
            patch("app.services.llm.gemini.GEMINI_API_KEY", "fake-key"),
            patch("app.services.llm.gemini.genai"),
        ):
            provider = GeminiProvider()
        if side_effect is not None:
            provider.client.models.generate_content = MagicMock(side_effect=side_effect)
        else:
            provider.client.models.generate_content = MagicMock(
                return_value=_make_response(response_text)
            )
        return provider

    return _make


@pytest.fixture
def no_sleep():
    with patch("app.services.llm.gemini.time.sleep") as mock_sleep:
        yield mock_sleep


def _called_models(provider):
    calls = provider.client.models.generate_content.call_args_list
    return [call.kwargs.get("model") for call in calls]


def build_prompt(content="msg", sender="Bank", categories=None, banks=None):
    return _ConcreteProvider().build_message_parse_prompt(
        content, sender, categories or [], banks
    )


# --- Category-only behavior (backward compat) ---


def test_returns_matching_category(make_provider):
    provider = make_provider('{"category": "finance"}')
    result = provider.parse_message("Paid $50", "Bank", ["finance", "personal"])
    assert result == MessageParseResult(category="finance")


def test_returns_empty_for_uncategorized(make_provider):
    provider = make_provider('{"category": "uncategorized"}')
    result = provider.parse_message("Hello", "Unknown", ["finance"])
    assert result == MessageParseResult()


def test_short_circuits_when_both_empty(make_provider):
    provider = make_provider()
    result = provider.parse_message("Hello", "X", [], [])
    assert result == MessageParseResult()
    provider.client.models.generate_content.assert_not_called()


def test_calls_llm_when_banks_present_but_no_categories(make_provider):
    provider = make_provider('{"bank": "BRAC Bank", "balance": 1000}')
    result = provider.parse_message("Balance: 1000", "BRACBANK", [], ["BRAC Bank"])
    assert result == MessageParseResult(bank="BRAC Bank", balance=Decimal("1000"))


def test_calls_llm_when_categories_present_but_no_banks(make_provider):
    provider = make_provider('{"category": "finance"}')
    result = provider.parse_message("Paid $50", "Bank", ["finance"], [])
    assert result == MessageParseResult(category="finance")


def test_returns_empty_for_empty_response(make_provider):
    provider = make_provider(None)
    result = provider.parse_message("Hello", "X", ["finance"])
    assert result == MessageParseResult()


def test_case_insensitive_category_match(make_provider):
    provider = make_provider('{"category": "Finance"}')
    result = provider.parse_message("Paid $50", "Bank", ["finance"])
    assert result == MessageParseResult(category="finance")


def test_returns_empty_for_unknown_category(make_provider):
    provider = make_provider('{"category": "sports"}')
    result = provider.parse_message("Hello", "X", ["finance", "personal"])
    assert result == MessageParseResult()


def test_propagates_api_error(make_provider):
    provider = make_provider()
    provider.client.models.generate_content = MagicMock(
        side_effect=RuntimeError("API down")
    )
    with pytest.raises(RuntimeError):
        provider.parse_message("Hello", "X", ["finance"])


# --- Bank + balance extraction ---


def test_extracts_bank_and_balance(make_provider):
    provider = make_provider(
        '{"category": "transaction", "bank": "BRAC Bank PLC", "balance": 2000}'
    )
    result = provider.parse_message(
        "Balance: 2000 BDT",
        "BRACBANK",
        ["transaction"],
        ["BRAC Bank PLC"],
    )
    assert result == MessageParseResult(
        category="transaction",
        bank="BRAC Bank PLC",
        balance=Decimal("2000"),
    )


def test_bank_present_balance_null(make_provider):
    provider = make_provider(
        '{"category": "transaction", "bank": "BRAC", "balance": null}'
    )
    result = provider.parse_message(
        "Some transaction", "BRAC", ["transaction"], ["BRAC"]
    )
    assert result == MessageParseResult(category="transaction", bank="BRAC")


def test_balance_present_bank_null_is_orphan_stripped(make_provider):
    provider = make_provider(
        '{"category": "transaction", "bank": null, "balance": 500}'
    )
    result = provider.parse_message("Balance: 500", "X", ["transaction"], ["BRAC Bank"])
    assert result == MessageParseResult(category="transaction")


def test_balance_float(make_provider):
    provider = make_provider('{"bank": "BRAC", "balance": 100.25}')
    result = provider.parse_message("Balance: 100.25", "BRAC", [], ["BRAC"])
    assert result.balance == Decimal("100.25")


def test_bank_case_insensitive_match(make_provider):
    provider = make_provider('{"bank": "brac bank plc", "balance": 100}')
    result = provider.parse_message("x", "x", [], ["BRAC Bank PLC"])
    assert result.bank == "BRAC Bank PLC"


def test_bank_not_in_list(make_provider):
    provider = make_provider('{"bank": "Some Other Bank", "balance": 100}')
    result = provider.parse_message("x", "x", [], ["BRAC Bank PLC"])
    assert result == MessageParseResult()


# --- Prompt builder ---


def test_prompt_includes_categories_section_when_present():
    prompt = build_prompt(categories=["finance", "personal"])
    assert "Categories:" in prompt
    assert '"finance"' in prompt
    assert "Banks:" not in prompt


def test_prompt_includes_banks_section_when_present():
    prompt = build_prompt(banks=["BRAC Bank PLC", "EBL"])
    assert "Banks:" in prompt
    assert '"BRAC Bank PLC"' in prompt
    assert '"EBL"' in prompt
    assert "Categories:" not in prompt


def test_prompt_includes_both_sections():
    prompt = build_prompt(categories=["transaction"], banks=["BRAC"])
    assert "Categories:" in prompt
    assert "Banks:" in prompt
    assert '"category"' in prompt
    assert '"bank"' in prompt
    assert '"balance"' in prompt


def test_prompt_response_shape_is_always_full():
    # The response JSON always carries all three keys regardless of input,
    # with null for unavailable fields.
    for kwargs in (
        {"categories": ["finance"]},
        {"banks": ["BRAC"]},
        {"categories": ["finance"], "banks": ["BRAC"]},
    ):
        prompt = build_prompt(**kwargs)
        assert '"category"' in prompt
        assert '"bank"' in prompt
        assert '"balance"' in prompt


def test_prompt_includes_message_content_and_sender():
    prompt = build_prompt(
        content="You paid 50 BDT", sender="BRACBANK", categories=["transaction"]
    )
    assert "BRACBANK" in prompt
    assert "You paid 50 BDT" in prompt


# --- Retry / fallthrough ---


PRIMARY, FALLBACK = GeminiProvider.MODELS


def test_fallthrough_to_second_model_on_429(make_provider, no_sleep):
    provider = make_provider(
        side_effect=[_api_error(429), _make_response('{"category": "finance"}')]
    )
    result = provider.parse_message("Paid $50", "Bank", ["finance"])
    assert result == MessageParseResult(category="finance")
    assert _called_models(provider) == [PRIMARY, FALLBACK]
    no_sleep.assert_not_called()


def test_fallthrough_to_second_model_on_503(make_provider, no_sleep):
    provider = make_provider(
        side_effect=[_api_error(503), _make_response('{"category": "finance"}')]
    )
    result = provider.parse_message("Paid $50", "Bank", ["finance"])
    assert result == MessageParseResult(category="finance")
    assert _called_models(provider) == [PRIMARY, FALLBACK]
    no_sleep.assert_not_called()


def test_retry_cycle_on_both_models_failing(make_provider, no_sleep):
    provider = make_provider(
        side_effect=[
            _api_error(429),
            _api_error(503),
            _make_response('{"category": "finance"}'),
        ]
    )
    result = provider.parse_message("Paid $50", "Bank", ["finance"])
    assert result == MessageParseResult(category="finance")
    assert _called_models(provider) == [PRIMARY, FALLBACK, PRIMARY]
    assert no_sleep.call_count == 1


def test_exhausts_max_cycles_and_raises(make_provider, no_sleep):
    total_calls = GeminiProvider.MAX_CYCLES * len(GeminiProvider.MODELS)
    provider = make_provider(side_effect=[_api_error(503) for _ in range(total_calls)])
    with pytest.raises(genai_errors.APIError):
        provider.parse_message("Paid $50", "Bank", ["finance"])
    assert provider.client.models.generate_content.call_count == total_calls
    assert no_sleep.call_count == GeminiProvider.MAX_CYCLES - 1


def test_non_retryable_error_raises_immediately(make_provider, no_sleep):
    provider = make_provider(side_effect=[_api_error(400)])
    with pytest.raises(genai_errors.APIError):
        provider.parse_message("Paid $50", "Bank", ["finance"])
    assert provider.client.models.generate_content.call_count == 1
    no_sleep.assert_not_called()


def test_timeout_error_is_retryable(make_provider, no_sleep):
    provider = make_provider(
        side_effect=[
            httpx.TimeoutException("timeout"),
            _make_response('{"category": "finance"}'),
        ]
    )
    result = provider.parse_message("Paid $50", "Bank", ["finance"])
    assert result == MessageParseResult(category="finance")
    assert _called_models(provider) == [PRIMARY, FALLBACK]
    no_sleep.assert_not_called()


def test_backoff_delay_grows_exponentially(make_provider, no_sleep):
    total_calls = GeminiProvider.MAX_CYCLES * len(GeminiProvider.MODELS)
    provider = make_provider(side_effect=[_api_error(503) for _ in range(total_calls)])
    with pytest.raises(genai_errors.APIError):
        provider.parse_message("Paid $50", "Bank", ["finance"])
    sleeps = [call.args[0] for call in no_sleep.call_args_list]
    assert sleeps == [
        GeminiProvider.BACKOFF_BASE_SECONDS,
        GeminiProvider.BACKOFF_BASE_SECONDS * 2,
    ]
