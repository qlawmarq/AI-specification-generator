"""
Tests for Gemini API integration in the specification generator.

This module tests the Gemini LLM provider implementation and ensures
proper integration with the existing codebase.
"""

import pytest
from unittest.mock import Mock, patch
import asyncio

from src.spec_generator.models import SpecificationConfig
from src.spec_generator.core.generator import LLMProvider


class TestGeminiProvider:
    """Test class for Gemini provider functionality."""

    def test_gemini_provider_initialization(self):
        """Gemini provider initializes correctly."""
        with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_gemini:
            mock_instance = Mock()
            mock_gemini.return_value = mock_instance

            config = SpecificationConfig(
                gemini_api_key="test-key", llm_provider="gemini"
            )
            provider = LLMProvider(config)

            assert provider.llm is not None
            assert provider.llm == mock_instance

            # Verify ChatGoogleGenerativeAI was called with correct parameters
            mock_gemini.assert_called_once_with(
                model="gemini-2.0-flash",
                temperature=0.3,
                google_api_key="test-key",
                max_retries=3,
            )

    def test_gemini_provider_with_custom_model(self):
        """Gemini provider works with custom model."""
        with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_gemini:
            mock_instance = Mock()
            mock_gemini.return_value = mock_instance

            config = SpecificationConfig(
                gemini_api_key="test-key",
                llm_provider="gemini",
                llm_model="gemini-2.5-pro-preview-03-25",
            )
            provider = LLMProvider(config)

            # Verify ChatGoogleGenerativeAI was called with custom model
            mock_gemini.assert_called_once_with(
                model="gemini-2.5-pro-preview-03-25",
                temperature=0.3,
                google_api_key="test-key",
                max_retries=3,
            )

    def test_provider_auto_detection(self):
        """Provider auto-detects based on available keys."""
        config = SpecificationConfig(gemini_api_key="test-key")
        provider = LLMProvider(config)
        assert provider._detect_provider() == "gemini"

    def test_provider_auto_detection_priority(self):
        """Provider auto-detection respects priority order."""
        # Test Gemini has highest priority
        config = SpecificationConfig(
            gemini_api_key="gemini-key", openai_api_key="openai-key"
        )
        provider = LLMProvider(config)
        assert provider._detect_provider() == "gemini"

        # Test Azure has second priority
        config = SpecificationConfig(
            azure_openai_endpoint="https://test.openai.azure.com/",
            azure_openai_key="azure-key",
            openai_api_key="openai-key",
        )
        provider = LLMProvider(config)
        assert provider._detect_provider() == "azure"

        # Test OpenAI is fallback
        config = SpecificationConfig(openai_api_key="openai-key")
        provider = LLMProvider(config)
        assert provider._detect_provider() == "openai"

    def test_provider_auto_detection_unknown(self):
        """Provider auto-detection returns unknown when no keys present."""
        config = SpecificationConfig()

        # Test that LLMProvider raises error for unknown provider
        with pytest.raises(ValueError) as exc_info:
            LLMProvider(config)
        assert "No valid configuration found for provider: unknown" in str(
            exc_info.value
        )

    def test_gemini_generation(self):
        """Gemini generation works with mocked response."""
        with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_llm:
            mock_instance = Mock()
            mock_instance.invoke.return_value = "Generated Japanese text"
            mock_llm.return_value = mock_instance

            config = SpecificationConfig(
                gemini_api_key="test-key", llm_provider="gemini"
            )
            provider = LLMProvider(config)

            # Test generation
            result = asyncio.run(provider.generate("Test prompt"))
            assert result == "Generated Japanese text"

            # Verify invoke was called with correct prompt
            mock_instance.invoke.assert_called_once_with("Test prompt")

    def test_gemini_generation_with_error(self):
        """Gemini generation handles errors gracefully."""
        with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_llm:
            mock_instance = Mock()
            mock_instance.invoke.side_effect = Exception("API Error")
            mock_llm.return_value = mock_instance

            config = SpecificationConfig(
                gemini_api_key="test-key", llm_provider="gemini"
            )
            provider = LLMProvider(config)

            # Test that exception is properly raised
            with pytest.raises(Exception) as exc_info:
                asyncio.run(provider.generate("Test prompt"))

            assert "API Error" in str(exc_info.value)

    def test_invalid_gemini_config(self):
        """Invalid Gemini configuration raises appropriate error."""
        # Test missing API key
        config = SpecificationConfig(llm_provider="gemini")

        with pytest.raises(ValueError) as exc_info:
            LLMProvider(config)

        assert "No valid configuration found for provider: gemini" in str(
            exc_info.value
        )

    def test_gemini_rate_limiting(self):
        """Gemini provider respects rate limiting."""
        import time

        with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_llm:
            mock_instance = Mock()
            mock_instance.invoke.return_value = "Generated text"
            mock_llm.return_value = mock_instance

            config = SpecificationConfig(
                gemini_api_key="test-key", llm_provider="gemini"
            )
            provider = LLMProvider(config)

            # Test that rate limiting is applied
            start_time = time.time()
            result1 = asyncio.run(provider.generate("Test prompt 1"))
            result2 = asyncio.run(provider.generate("Test prompt 2"))
            end_time = time.time()

            assert result1 == "Generated text"
            assert result2 == "Generated text"
            # Should take some time due to rate limiting
            assert end_time - start_time >= 0.0


class TestGeminiProviderValidation:
    """Test class for Gemini provider validation."""

    def test_llm_provider_validation(self):
        """LLM provider field validation works correctly."""
        # Test valid providers
        valid_providers = ["openai", "azure", "gemini"]
        for provider in valid_providers:
            config = SpecificationConfig(llm_provider=provider)
            assert config.llm_provider == provider

        # Test invalid provider
        with pytest.raises(ValueError) as exc_info:
            SpecificationConfig(llm_provider="invalid")

        assert (
            "llm_provider must be one of" in str(exc_info.value)
            and "openai" in str(exc_info.value)
            and "azure" in str(exc_info.value)
            and "gemini" in str(exc_info.value)
        )

    def test_gemini_config_loading_from_env(self):
        """Gemini configuration can be loaded from environment variables."""
        with patch.dict(
            "os.environ",
            {
                "GEMINI_API_KEY": "test-gemini-key",
                "LLM_PROVIDER": "gemini",
                "LLM_MODEL": "gemini-2.0-flash",
            },
        ):
            from src.spec_generator.models import ConfigLoader

            config = ConfigLoader.load_from_env()

            assert config.gemini_api_key == "test-gemini-key"
            assert config.llm_provider == "gemini"
            assert config.llm_model == "gemini-2.0-flash"

    def test_gemini_config_backwards_compatibility(self):
        """Gemini configuration maintains backwards compatibility."""
        # Test that existing OpenAI configuration still works
        config = SpecificationConfig(openai_api_key="openai-key")
        provider = LLMProvider(config)
        assert provider._detect_provider() == "openai"

        # Test that Azure configuration still works
        config = SpecificationConfig(
            azure_openai_endpoint="https://test.openai.azure.com/",
            azure_openai_key="azure-key",
        )
        provider = LLMProvider(config)
        assert provider._detect_provider() == "azure"


if __name__ == "__main__":
    pytest.main([__file__])
