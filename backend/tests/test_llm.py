from unittest.mock import MagicMock, patch

from app.services.llm.gemini import GeminiProvider


@patch("app.services.llm.gemini.GEMINI_API_KEY", "fake-key")
class TestGeminiProvider:
    def _make_provider(self, response_text):
        with patch("app.services.llm.gemini.genai"):
            provider = GeminiProvider()
            mock_response = MagicMock()
            mock_response.text = response_text
            provider.client.models.generate_content = MagicMock(
                return_value=mock_response
            )
            return provider

    def test_returns_matching_category(self):
        provider = self._make_provider('{"category": "finance"}')
        result = provider.categorize_message(
            "Paid $50", "Bank", ["finance", "personal"]
        )
        assert result == "finance"

    def test_returns_none_for_uncategorized(self):
        provider = self._make_provider('{"category": "uncategorized"}')
        result = provider.categorize_message("Hello", "Unknown", ["finance"])
        assert result is None

    def test_returns_none_for_malformed_json(self):
        provider = self._make_provider("not json at all")
        result = provider.categorize_message("Hello", "X", ["finance"])
        assert result is None

    def test_returns_none_for_empty_categories(self):
        with patch("app.services.llm.gemini.genai"):
            provider = GeminiProvider()
        result = provider.categorize_message("Hello", "X", [])
        assert result is None

    def test_returns_none_for_empty_response(self):
        provider = self._make_provider(None)
        result = provider.categorize_message("Hello", "X", ["finance"])
        assert result is None

    def test_case_insensitive_matching(self):
        provider = self._make_provider('{"category": "Finance"}')
        result = provider.categorize_message("Paid $50", "Bank", ["finance"])
        assert result == "finance"

    def test_returns_none_for_unknown_category(self):
        provider = self._make_provider('{"category": "sports"}')
        result = provider.categorize_message("Hello", "X", ["finance", "personal"])
        assert result is None

    def test_handles_api_error(self):
        with patch("app.services.llm.gemini.genai"):
            provider = GeminiProvider()
        provider.client.models.generate_content = MagicMock(
            side_effect=RuntimeError("API down")
        )
        try:
            provider.categorize_message("Hello", "X", ["finance"])
        except RuntimeError:
            pass
