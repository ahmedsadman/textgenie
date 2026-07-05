from decimal import Decimal
from unittest.mock import MagicMock, patch

import httpx
import pytest
from google.genai import errors as genai_errors

from app.services.llm import gemini as gemini_module
from app.services.llm.base import LLMProvider, MetadataResult, ParsePrompt
from app.services.llm.gemini import GeminiProvider


class _ConcreteProvider(LLMProvider):
    def categorize(self, *a, **k):  # pragma: no cover - prompt-builder tests only
        raise NotImplementedError

    def extract_metadata(self, *a, **k):  # pragma: no cover - prompt-builder tests only
        raise NotImplementedError


def _make_response(text):
    response = MagicMock()
    response.text = text
    response.usage_metadata.prompt_token_count = 100
    response.usage_metadata.cached_content_token_count = 0
    response.usage_metadata.candidates_token_count = 20
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


# --- categorize() ---


def test_categorize_returns_matching_name(make_provider):
    provider = make_provider('{"category": "finance"}')
    assert provider.categorize("Paid $50", "Bank", ["finance", "personal"]) == "finance"


def test_categorize_returns_none_for_uncategorized(make_provider):
    provider = make_provider('{"category": "uncategorized"}')
    assert provider.categorize("Hello", "Unknown", ["finance"]) is None


def test_categorize_returns_none_for_unknown_category(make_provider):
    provider = make_provider('{"category": "sports"}')
    assert provider.categorize("Hello", "X", ["finance", "personal"]) is None


def test_categorize_case_insensitive_match(make_provider):
    provider = make_provider('{"category": "Finance"}')
    assert provider.categorize("Paid $50", "Bank", ["finance"]) == "finance"


def test_categorize_short_circuits_when_no_categories(make_provider):
    provider = make_provider()
    assert provider.categorize("Hello", "X", []) is None
    provider.client.models.generate_content.assert_not_called()


def test_categorize_returns_none_for_empty_response(make_provider):
    provider = make_provider(None)
    assert provider.categorize("Hello", "X", ["finance"]) is None


def test_categorize_propagates_non_retryable_error(make_provider):
    provider = make_provider()
    provider.client.models.generate_content = MagicMock(
        side_effect=RuntimeError("API down")
    )
    with pytest.raises(RuntimeError):
        provider.categorize("Hello", "X", ["finance"])


# --- extract_metadata() ---


def test_extract_metadata_bank_and_balance(make_provider):
    provider = make_provider(
        '{"bank": "BRAC Bank PLC", "balance": 2000, "original_currency": "BDT"}'
    )
    result = provider.extract_metadata(
        "Balance: 2000 BDT", "BRACBANK", ["BRAC Bank PLC"], "BDT"
    )
    assert result == MetadataResult(
        bank="BRAC Bank PLC", balance=Decimal("2000"), original_currency="BDT"
    )


def test_extract_metadata_bank_present_balance_null(make_provider):
    provider = make_provider('{"bank": "BRAC", "balance": null}')
    result = provider.extract_metadata("Some transaction", "BRAC", ["BRAC"], "BDT")
    assert result == MetadataResult(bank="BRAC")


def test_extract_metadata_balance_present_bank_null_is_orphan_stripped(make_provider):
    provider = make_provider('{"bank": null, "balance": 500}')
    result = provider.extract_metadata("Balance: 500", "X", ["BRAC Bank"], "BDT")
    assert result == MetadataResult()


def test_extract_metadata_balance_float(make_provider):
    provider = make_provider(
        '{"bank": "BRAC", "balance": 100.25, "original_currency": "BDT"}'
    )
    result = provider.extract_metadata("Balance: 100.25", "BRAC", ["BRAC"], "BDT")
    assert result.balance == Decimal("100.25")


def test_extract_metadata_case_insensitive_bank_match(make_provider):
    provider = make_provider(
        '{"bank": "brac bank plc", "balance": 100, "original_currency": "BDT"}'
    )
    result = provider.extract_metadata("x", "x", ["BRAC Bank PLC"], "BDT")
    assert result.bank == "BRAC Bank PLC"


def test_extract_metadata_bank_not_in_list(make_provider):
    provider = make_provider(
        '{"bank": "Some Other Bank", "balance": 100, "original_currency": "BDT"}'
    )
    result = provider.extract_metadata("x", "x", ["BRAC Bank PLC"], "BDT")
    assert result == MetadataResult()


def test_extract_metadata_short_circuits_when_no_banks(make_provider):
    provider = make_provider()
    assert provider.extract_metadata("x", "x", [], "BDT") == MetadataResult()
    provider.client.models.generate_content.assert_not_called()


def test_extract_metadata_returns_empty_for_empty_response(make_provider):
    provider = make_provider(None)
    assert provider.extract_metadata("x", "x", ["BRAC"], "BDT") == MetadataResult()


def test_extract_metadata_returns_original_currency_and_amount(make_provider):
    provider = make_provider(
        '{"bank": "EBL", "balance": 60000, "amount": 12000, '
        '"original_amount": 100, '
        '"transaction_type": "expense", "original_currency": "usd"}'
    )
    result = provider.extract_metadata("Purchase USD 100", "EBL", ["EBL"], "BDT")
    assert result == MetadataResult(
        bank="EBL",
        balance=Decimal("60000"),
        amount=Decimal("12000"),
        transaction_type="expense",
        original_currency="USD",
        original_amount=Decimal("100"),
    )


def test_extract_metadata_drops_original_amount_when_amount_missing(make_provider):
    """If `amount` is null (invalid pair), `original_amount` is also cleared."""
    provider = make_provider(
        '{"bank": "EBL", "balance": 60000, "amount": null, '
        '"original_amount": 100, '
        '"transaction_type": null, "original_currency": "USD"}'
    )
    result = provider.extract_metadata("balance only msg", "EBL", ["EBL"], "BDT")
    assert result.amount is None
    assert result.original_amount is None
    # balance survives — original_currency stays because balance is present.
    assert result.balance == Decimal("60000")
    assert result.original_currency == "USD"


def test_extract_metadata_original_amount_same_as_amount_when_no_conversion(
    make_provider,
):
    provider = make_provider(
        '{"bank": "BRAC", "balance": 2000, "amount": 50, '
        '"original_amount": 50, '
        '"transaction_type": "expense", "original_currency": "BDT"}'
    )
    result = provider.extract_metadata("debit 50 BDT", "BRAC", ["BRAC"], "BDT")
    assert result.amount == Decimal("50")
    assert result.original_amount == Decimal("50")


def test_extract_metadata_drops_currency_when_no_amount_or_balance(make_provider):
    provider = make_provider(
        '{"bank": "EBL", "balance": null, "amount": null, '
        '"original_amount": null, '
        '"transaction_type": null, "original_currency": "USD"}'
    )
    result = provider.extract_metadata("statement ready", "EBL", ["EBL"], "BDT")
    assert result.original_currency is None
    assert result.original_amount is None


def test_extract_metadata_invalid_currency_string_becomes_none(make_provider):
    provider = make_provider(
        '{"bank": "EBL", "balance": 100, "original_currency": "dollars"}'
    )
    result = provider.extract_metadata("x", "x", ["EBL"], "BDT")
    assert result.original_currency is None


# --- Prompt builders ---


def test_categorize_prompt_contains_categories_and_message():
    prompt = _ConcreteProvider().build_categorize_prompt(
        "You paid 50 BDT", "BRACBANK", ["transaction", "personal"]
    )
    assert isinstance(prompt, ParsePrompt)
    assert "Categories:" in prompt.contents
    assert '"transaction"' in prompt.contents
    assert '"personal"' in prompt.contents
    assert "BRACBANK" in prompt.contents
    assert "You paid 50 BDT" in prompt.contents
    assert '"category"' in prompt.system_instruction
    assert '"bank"' not in prompt.system_instruction


def test_metadata_prompt_contains_banks_and_message():
    prompt = _ConcreteProvider().build_metadata_prompt(
        "Balance: 2000", "BRACBANK", ["BRAC Bank PLC", "EBL"], "BDT"
    )
    assert isinstance(prompt, ParsePrompt)
    assert "Banks:" in prompt.contents
    assert '"BRAC Bank PLC"' in prompt.contents
    assert '"EBL"' in prompt.contents
    assert "BRACBANK" in prompt.contents
    assert "Balance: 2000" in prompt.contents
    assert "BDT" in prompt.contents
    assert '"bank"' in prompt.system_instruction
    assert '"balance"' in prompt.system_instruction
    assert '"original_currency"' in prompt.system_instruction
    assert '"original_amount"' in prompt.system_instruction
    assert '"category"' not in prompt.system_instruction


def test_metadata_prompt_includes_normalized_currency():
    prompt = _ConcreteProvider().build_metadata_prompt(
        "Balance: 100 USD", "EBL", ["EBL"], "USD"
    )
    assert "USD" in prompt.contents
    assert "Normalized currency: USD" in prompt.contents


# --- Retry / fallthrough (exercises shared _generate_with_fallback) ---


PRIMARY, FALLBACK = GeminiProvider.MODELS


def test_fallthrough_to_second_model_on_429(make_provider, no_sleep):
    provider = make_provider(
        side_effect=[_api_error(429), _make_response('{"category": "finance"}')]
    )
    assert provider.categorize("Paid $50", "Bank", ["finance"]) == "finance"
    assert _called_models(provider) == [PRIMARY, FALLBACK]
    no_sleep.assert_not_called()


def test_fallthrough_to_second_model_on_503(make_provider, no_sleep):
    provider = make_provider(
        side_effect=[_api_error(503), _make_response('{"category": "finance"}')]
    )
    assert provider.categorize("Paid $50", "Bank", ["finance"]) == "finance"
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
    assert provider.categorize("Paid $50", "Bank", ["finance"]) == "finance"
    assert _called_models(provider) == [PRIMARY, FALLBACK, PRIMARY]
    assert no_sleep.call_count == 1


def test_exhausts_max_cycles_and_raises(make_provider, no_sleep):
    total_calls = GeminiProvider.MAX_CYCLES * len(GeminiProvider.MODELS)
    provider = make_provider(side_effect=[_api_error(503) for _ in range(total_calls)])
    with pytest.raises(genai_errors.APIError):
        provider.categorize("Paid $50", "Bank", ["finance"])
    assert provider.client.models.generate_content.call_count == total_calls
    assert no_sleep.call_count == GeminiProvider.MAX_CYCLES - 1


def test_non_retryable_error_raises_immediately(make_provider, no_sleep):
    provider = make_provider(side_effect=[_api_error(400)])
    with pytest.raises(genai_errors.APIError):
        provider.categorize("Paid $50", "Bank", ["finance"])
    assert provider.client.models.generate_content.call_count == 1
    no_sleep.assert_not_called()


def test_timeout_error_is_retryable(make_provider, no_sleep):
    provider = make_provider(
        side_effect=[
            httpx.TimeoutException("timeout"),
            _make_response('{"category": "finance"}'),
        ]
    )
    assert provider.categorize("Paid $50", "Bank", ["finance"]) == "finance"
    assert _called_models(provider) == [PRIMARY, FALLBACK]
    no_sleep.assert_not_called()


def test_backoff_delay_grows_exponentially(make_provider, no_sleep):
    total_calls = GeminiProvider.MAX_CYCLES * len(GeminiProvider.MODELS)
    provider = make_provider(side_effect=[_api_error(503) for _ in range(total_calls)])
    with pytest.raises(genai_errors.APIError):
        provider.categorize("Paid $50", "Bank", ["finance"])
    sleeps = [call.args[0] for call in no_sleep.call_args_list]
    assert sleeps == [
        GeminiProvider.BACKOFF_BASE_SECONDS,
        GeminiProvider.BACKOFF_BASE_SECONDS * 2,
    ]


def test_extract_metadata_uses_same_retry_logic(make_provider, no_sleep):
    provider = make_provider(
        side_effect=[
            _api_error(429),
            _make_response(
                '{"bank": "BRAC", "balance": 50, "original_currency": "BDT"}'
            ),
        ]
    )
    result = provider.extract_metadata("x", "x", ["BRAC"], "BDT")
    assert result == MetadataResult(
        bank="BRAC", balance=Decimal("50"), original_currency="BDT"
    )
    assert _called_models(provider) == [PRIMARY, FALLBACK]


# --- Model usage stats ---


@pytest.fixture(autouse=True)
def _reset_model_stats():
    gemini_module._model_counts.clear()
    gemini_module._total_requests = 0
    yield


def test_model_stats_logged_every_10_requests(make_provider, caplog):
    provider = make_provider('{"category": "finance"}')
    for _ in range(10):
        provider.categorize("Paid $50", "Bank", ["finance"])
    assert "LLM model stats (total=10)" in caplog.text
    assert f"{PRIMARY}=100.0%" in caplog.text


def test_model_stats_not_logged_before_10(make_provider, caplog):
    provider = make_provider('{"category": "finance"}')
    for _ in range(9):
        provider.categorize("Paid $50", "Bank", ["finance"])
    assert "LLM model stats" not in caplog.text


def test_model_stats_includes_fallback(make_provider, no_sleep, caplog):
    responses = []
    for _ in range(10):
        responses.extend([_api_error(429), _make_response('{"category": "f"}')])
    provider = make_provider(side_effect=responses)
    for _ in range(10):
        provider.categorize("Paid $50", "Bank", ["finance"])
    assert "LLM model stats (total=10)" in caplog.text
    assert f"{FALLBACK}=100.0%" in caplog.text


def test_model_stats_counts_metadata_calls_too(make_provider, caplog):
    provider = make_provider(
        '{"bank": "BRAC", "balance": 100, "original_currency": "BDT"}'
    )
    for _ in range(10):
        provider.extract_metadata("x", "x", ["BRAC"], "BDT")
    assert "LLM model stats (total=10)" in caplog.text
