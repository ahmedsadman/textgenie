from app.services.llm.base import LLMProvider
from app.services.llm.gemini import GeminiProvider

_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        _provider = GeminiProvider()
    return _provider
