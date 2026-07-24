from google import genai

from app.config import GEMINI_API_KEY
from app.services.llm.base import LLMProvider
from app.services.llm.gemini import GeminiProvider
from app.services.llm.usage import LLMUsageEvent, record_from_current_session

_client: genai.Client | None = None


def _get_shared_client() -> genai.Client:
    """Lazy module-level cache of the genai.Client.

    Sharing the client (and its httpx connection pool) across per-request
    provider instances avoids TCP+TLS handshake overhead on every LLM call.
    """
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def build_provider(user_id: int) -> LLMProvider:
    """Build a fresh provider bound to a specific user for the current request."""

    def recorder(event: LLMUsageEvent) -> None:
        record_from_current_session(user_id, event)

    return GeminiProvider(client=_get_shared_client(), recorder=recorder)
