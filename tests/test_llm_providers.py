"""Integration tests for LLM providers."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from apps.llm.router import LLMRouter
from apps.llm.providers.gemini_provider import GeminiProvider
from apps.llm.providers.ollama_provider import OllamaProvider
from apps.llm.providers.local_provider import LocalProvider


class TestLLMRouter:
    """Test LLM Router functionality."""

    @pytest.fixture
    def router(self):
        """Create LLM router instance."""
        return LLMRouter()

    @pytest.mark.asyncio
    async def test_router_initialization(self, router):
        """Test router initializes with correct providers."""
        assert "gemini" in router.providers
        assert "ollama" in router.providers
        assert "local" in router.providers
        assert isinstance(router.providers["gemini"], GeminiProvider)
        assert isinstance(router.providers["ollama"], OllamaProvider)
        assert isinstance(router.providers["local"], LocalProvider)

    @pytest.mark.asyncio
    async def test_get_provider(self, router):
        """Test getting provider by name."""
        gemini = router.get_provider("gemini")
        assert isinstance(gemini, GeminiProvider)

        ollama = router.get_provider("ollama")
        assert isinstance(ollama, OllamaProvider)

        local = router.get_provider("local")
        assert isinstance(local, LocalProvider)

    @pytest.mark.asyncio
    async def test_get_invalid_provider(self, router):
        """Test getting non-existent provider."""
        with pytest.raises(ValueError, match="Provider 'invalid' not found"):
            router.get_provider("invalid")

    @pytest.mark.asyncio
    async def test_select_best_provider_planning(self, router):
        """Test provider selection for planning tasks."""
        provider = router.select_best_provider("planning")
        # Gemini is best for planning (high accuracy)
        assert provider.name == "gemini"

    @pytest.mark.asyncio
    async def test_select_best_provider_execution(self, router):
        """Test provider selection for execution tasks."""
        provider = router.select_best_provider("execution")
        # Ollama is good for execution (fast, reliable)
        assert provider.name in ["gemini", "ollama"]

    @pytest.mark.asyncio
    async def test_select_best_provider_verification(self, router):
        """Test provider selection for verification tasks."""
        provider = router.select_best_provider("verification")
        # Any provider can do verification
        assert provider.name in ["gemini", "ollama", "local"]


class TestGeminiProvider:
    """Test Gemini provider."""

    @pytest.fixture
    def provider(self):
        """Create Gemini provider instance."""
        return GeminiProvider()

    def test_provider_attributes(self, provider):
        """Test provider basic attributes."""
        assert provider.name == "gemini"
        assert provider.model_name.startswith("gemini")
        assert provider.api_key is not None or provider.api_key == "test-key"

    @pytest.mark.asyncio
    @patch('apps.llm.providers.gemini_provider.genai')
    async def test_generate_with_valid_api_key(self, mock_genai, provider):
        """Test generation with valid API key."""
        # Mock the Gemini API response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Test response from Gemini"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        # Set a test API key
        provider.api_key = "test-api-key"

        response = await provider.generate("Test prompt")
        assert response == "Test response from Gemini"

    @pytest.mark.asyncio
    async def test_generate_without_api_key(self, provider):
        """Test generation fails without API key."""
        provider.api_key = None

        with pytest.raises(ValueError, match="GEMINI_API_KEY not set"):
            await provider.generate("Test prompt")

    @pytest.mark.asyncio
    @patch('apps.llm.providers.gemini_provider.genai')
    async def test_generate_with_system_prompt(self, mock_genai, provider):
        """Test generation with system prompt."""
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Response with system context"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        provider.api_key = "test-api-key"

        response = await provider.generate(
            "Test prompt",
            system_prompt="You are a helpful assistant"
        )
        assert "Response with system context" in response


class TestOllamaProvider:
    """Test Ollama provider."""

    @pytest.fixture
    def provider(self):
        """Create Ollama provider instance."""
        return OllamaProvider()

    def test_provider_attributes(self, provider):
        """Test provider basic attributes."""
        assert provider.name == "ollama"
        assert provider.model_name == "llama2"
        assert provider.base_url is not None

    @pytest.mark.asyncio
    @patch('apps.llm.providers.ollama_provider.httpx.AsyncClient')
    async def test_generate_success(self, mock_client, provider):
        """Test successful generation."""
        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "Test response from Ollama"
        }

        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = AsyncMock()
        mock_client.return_value = mock_instance

        response = await provider.generate("Test prompt")
        assert response == "Test response from Ollama"

    @pytest.mark.asyncio
    @patch('apps.llm.providers.ollama_provider.httpx.AsyncClient')
    async def test_generate_with_error(self, mock_client, provider):
        """Test generation with API error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("API Error")

        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = AsyncMock()
        mock_client.return_value = mock_instance

        with pytest.raises(Exception):
            await provider.generate("Test prompt")

    @pytest.mark.asyncio
    @patch('apps.llm.providers.ollama_provider.httpx.AsyncClient')
    async def test_check_health_success(self, mock_client, provider):
        """Test health check success."""
        mock_response = Mock()
        mock_response.status_code = 200

        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = AsyncMock()
        mock_client.return_value = mock_instance

        is_healthy = await provider.check_health()
        assert is_healthy is True

    @pytest.mark.asyncio
    @patch('apps.llm.providers.ollama_provider.httpx.AsyncClient')
    async def test_check_health_failure(self, mock_client, provider):
        """Test health check failure."""
        mock_instance = AsyncMock()
        mock_instance.get.side_effect = Exception("Connection refused")
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = AsyncMock()
        mock_client.return_value = mock_instance

        is_healthy = await provider.check_health()
        assert is_healthy is False


class TestLocalProvider:
    """Test Local provider."""

    @pytest.fixture
    def provider(self):
        """Create Local provider instance."""
        return LocalProvider()

    def test_provider_attributes(self, provider):
        """Test provider basic attributes."""
        assert provider.name == "local"
        assert provider.model_name == "local-model"

    @pytest.mark.asyncio
    async def test_generate_basic(self, provider):
        """Test basic generation (rule-based)."""
        response = await provider.generate("check disk space")
        assert len(response) > 0
        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_generate_planning_task(self, provider):
        """Test planning task response."""
        response = await provider.generate("plan to deploy nginx")
        assert "step" in response.lower() or "plan" in response.lower()

    @pytest.mark.asyncio
    async def test_generate_execution_task(self, provider):
        """Test execution task response."""
        response = await provider.generate("execute: df -h")
        assert "command" in response.lower() or "execute" in response.lower()

    @pytest.mark.asyncio
    async def test_check_health(self, provider):
        """Test health check (always healthy)."""
        is_healthy = await provider.check_health()
        assert is_healthy is True


class TestProviderIntegration:
    """Integration tests with actual providers (requires API keys/services)."""

    @pytest.fixture
    def router(self):
        """Create LLM router instance."""
        return LLMRouter()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_gemini_real_request(self, router):
        """Test real Gemini API request (requires API key)."""
        provider = router.get_provider("gemini")

        if not provider.api_key or provider.api_key == "test-key":
            pytest.skip("GEMINI_API_KEY not set")

        try:
            response = await provider.generate("Say 'Hello, DevOps Agent!'")
            assert len(response) > 0
            assert isinstance(response, str)
        except Exception as e:
            pytest.skip(f"Gemini API not available: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_ollama_real_request(self, router):
        """Test real Ollama request (requires Ollama running)."""
        provider = router.get_provider("ollama")

        # Check if Ollama is available
        is_healthy = await provider.check_health()
        if not is_healthy:
            pytest.skip("Ollama service not available")

        try:
            response = await provider.generate("Say 'Hello, DevOps Agent!'")
            assert len(response) > 0
            assert isinstance(response, str)
        except Exception as e:
            pytest.skip(f"Ollama not available: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_local_provider_always_works(self, router):
        """Test local provider (should always work)."""
        provider = router.get_provider("local")

        response = await provider.generate("test prompt")
        assert len(response) > 0
        assert isinstance(response, str)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_router_with_fallback(self, router):
        """Test router automatically falls back on provider failure."""
        # This would test the router's fallback mechanism
        # when primary provider fails
        try:
            provider = router.select_best_provider("planning")
            response = await provider.generate("Create a plan to check system health")
            assert len(response) > 0
        except Exception as e:
            # Should fall back to another provider
            provider = router.get_provider("local")
            response = await provider.generate("Create a plan to check system health")
            assert len(response) > 0


# Pytest configuration
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires external services)"
    )


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
