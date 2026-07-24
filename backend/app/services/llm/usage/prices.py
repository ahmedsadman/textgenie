"""LLM per-model price table (micro-USD per 1M tokens)."""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Price:
    input_per_mtok_micros: int
    output_per_mtok_micros: int
    cached_input_per_mtok_micros: int


# Gemini prices from https://ai.google.dev/gemini-api/docs/pricing
# Standard tier, paid, text modality. Verified 2026-07-24.
DEFAULT_PRICES: dict[tuple[str, str], Price] = {
    ("gemini", "gemini-2.5-flash-lite"): Price(
        input_per_mtok_micros=100_000,
        output_per_mtok_micros=400_000,
        cached_input_per_mtok_micros=10_000,
    ),
    ("gemini", "gemini-3.1-flash-lite"): Price(
        input_per_mtok_micros=250_000,
        output_per_mtok_micros=1_500_000,
        cached_input_per_mtok_micros=25_000,
    ),
}


def compute_cost_micros(
    provider: str,
    model: str,
    input_tokens: int,
    cached_input_tokens: int,
    output_tokens: int,
) -> int:
    """Return cost in micro-USD. Integer math, no float rounding.

    Returns 0 (and logs a warning) when the model is unknown.
    input_tokens is the TOTAL prompt INCLUDING cached; cached is subtracted
    to get the uncached billable portion.
    """
    price = DEFAULT_PRICES.get((provider, model))
    if price is None:
        logger.warning(
            "llm usage: unknown model, cost recorded as 0 (provider=%s, model=%s)",
            provider,
            model,
        )
        return 0
    uncached_input = max(input_tokens - cached_input_tokens, 0)
    return (
        (uncached_input * price.input_per_mtok_micros) // 1_000_000
        + (cached_input_tokens * price.cached_input_per_mtok_micros) // 1_000_000
        + (output_tokens * price.output_per_mtok_micros) // 1_000_000
    )
