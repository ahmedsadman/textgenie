from dataclasses import dataclass


@dataclass
class LLMUsageEvent:
    """Provider-agnostic per-call usage record.

    input_tokens is the TOTAL prompt INCLUDING cached; output_tokens includes
    any reasoning tokens billed at output rate. Adapters must normalize their
    SDK response to this shape.
    """

    provider: str
    model: str
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
