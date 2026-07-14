"""Tests for services/llm_providers.py — dispatch, registry, derivation.

Covers the dispatch logic from testcases.md:
- Provider auto-derivation (Task B fix: multi-provider + ambiguity error)
- PROVIDER_REGISTRY lookup
- get_provider factory
- predict_llm legacy wrapper
"""
import pytest
from services.llm_providers import (
    PROVIDER_REGISTRY,
    get_provider,
    _derive_provider,
    validate_provider_config,
    validate_per_model_config,
    predict_llm,
    OllamaProvider,
    OpenAIProvider,
    AnthropicProvider,
    VLLMProvider,
)


class TestProviderRegistry:
    """Tests for PROVIDER_REGISTRY dict."""

    def test_all_four_providers_registered(self):
        assert set(PROVIDER_REGISTRY.keys()) == {"ollama", "openai", "anthropic", "vllm", "custom_openai"}

    def test_ollama_class(self):
        assert PROVIDER_REGISTRY["ollama"] is OllamaProvider

    def test_openai_class(self):
        assert PROVIDER_REGISTRY["openai"] is OpenAIProvider

    def test_anthropic_class(self):
        assert PROVIDER_REGISTRY["anthropic"] is AnthropicProvider

    def test_vllm_class(self):
        assert PROVIDER_REGISTRY["vllm"] is VLLMProvider


class TestDeriveProvider:
    """Tests for _derive_provider (testcases.md: Task B — multi-provider derivation).

    Test cases from the ad-hoc verification (12 scenarios):
    - nothing set → ollama
    - explicit provider → that provider
    - single key → derive
    - multiple keys + no explicit → ValueError
    - explicit overrides key
    """

    def test_nothing_set_defaults_to_ollama(self):
        assert _derive_provider({}) == "ollama"

    def test_explicit_openai(self):
        assert _derive_provider({"llm_provider": "openai"}) == "openai"

    def test_explicit_ollama(self):
        assert _derive_provider({"llm_provider": "ollama"}) == "ollama"

    def test_explicit_anthropic(self):
        assert _derive_provider({"llm_provider": "anthropic"}) == "anthropic"

    def test_derives_from_openai_key(self):
        assert _derive_provider({"openai_key": "sk-xxx"}) == "openai"

    def test_derives_from_anthropic_key(self):
        assert _derive_provider({"anthropic_key": "sk-ant-xxx"}) == "anthropic"

    def test_derives_from_vllm_url(self):
        assert _derive_provider({"vllm_url": "http://localhost:8001/v1"}) == "vllm"

    def test_explicit_overrides_openai_key(self):
        result = _derive_provider({"openai_key": "sk-xxx", "llm_provider": "vllm"})
        assert result == "vllm"

    def test_explicit_overrides_anthropic_key(self):
        result = _derive_provider({"anthropic_key": "sk-ant-xxx", "llm_provider": "openai"})
        assert result == "openai"

    def test_multiple_keys_raises_value_error(self):
        with pytest.raises(ValueError, match="Multiple providers configured"):
            _derive_provider({"openai_key": "sk-x", "anthropic_key": "sk-ant-x"})

    def test_all_three_keys_raises(self):
        with pytest.raises(ValueError, match="Multiple providers configured"):
            _derive_provider({
                "openai_key": "sk-x", "anthropic_key": "sk-ant-x",
                "vllm_url": "http://l:8001"
            })

    def test_openai_plus_vllm_raises(self):
        with pytest.raises(ValueError, match="Multiple"):
            _derive_provider({"openai_key": "sk-x", "vllm_url": "http://l:8001"})

    def test_anthropic_plus_vllm_raises(self):
        with pytest.raises(ValueError, match="Multiple"):
            _derive_provider({"anthropic_key": "sk-ant-x", "vllm_url": "http://l:8001"})


class TestGetProvider:
    """Tests for get_provider factory."""

    def test_ollama_factory(self):
        provider = get_provider("ollama", {})
        assert isinstance(provider, OllamaProvider)

    def test_openai_factory(self):
        provider = get_provider("openai", {"openai_key": "sk-test"})
        assert isinstance(provider, OpenAIProvider)

    def test_anthropic_factory(self):
        provider = get_provider("anthropic", {"anthropic_key": "sk-ant-test"})
        assert isinstance(provider, AnthropicProvider)

    def test_vllm_factory(self):
        provider = get_provider("vllm", {"vllm_url": "http://localhost:8001/v1"})
        assert isinstance(provider, VLLMProvider)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_provider("nonexistent", {})

    def test_case_insensitive(self):
        provider = get_provider("OLLAMA", {})
        assert isinstance(provider, OllamaProvider)

    def test_provider_receives_config(self):
        config = {"test_key": "test_val"}
        provider = get_provider("ollama", config)
        assert provider.config["test_key"] == "test_val"


class TestPredictLlmWrapper:
    """Tests for predict_llm backward-compatible wrapper."""

    def test_predict_llm_importable(self):
        """predict_llm is importable (used by evaluation/eval.py)."""
        assert callable(predict_llm)
        assert predict_llm.__name__ == "predict_llm"


class TestValidateProviderConfig:
    """Tests for validate_provider_config."""

    def test_ollama_no_validation_needed(self):
        assert validate_provider_config("ollama", {}) == []

    def test_ollama_with_random_config(self):
        assert validate_provider_config("ollama", {"openai_key": "sk-x"}) == []

    def test_openai_with_key(self):
        assert validate_provider_config("openai", {"openai_key": "sk-xxx"}) == []

    def test_openai_without_key(self):
        errors = validate_provider_config("openai", {})
        assert len(errors) == 1
        assert "openai-key" in errors[0]

    def test_anthropic_with_key(self):
        assert validate_provider_config("anthropic", {"anthropic_key": "sk-ant-xxx"}) == []

    def test_anthropic_without_key(self):
        errors = validate_provider_config("anthropic", {})
        assert len(errors) == 1
        assert "anthropic-key" in errors[0]

    def test_vllm_with_url(self):
        assert validate_provider_config("vllm", {"vllm_url": "http://localhost:8001/v1"}) == []

    def test_vllm_without_url(self):
        errors = validate_provider_config("vllm", {})
        assert len(errors) == 1
        assert "vllm-url" in errors[0]

    def test_unknown_provider_returns_no_errors(self):
        assert validate_provider_config("nonexistent", {}) == []

    def test_empty_string_provider(self):
        assert validate_provider_config("", {}) == []


class TestValidatePerModelConfig:
    """Tests for validate_per_model_config (Phase 4: Live Compare Mode)."""

    def test_valid_model_a_config(self):
        """Fully configured model_a returns no errors."""
        config = {
            "model_a_provider": "openai",
            "model_a_model": "gpt-4o",
            "openai_key": "sk-test",
        }
        assert validate_per_model_config("model_a", config) == []

    def test_valid_model_b_config(self):
        """Fully configured model_b returns no errors."""
        config = {
            "model_b_provider": "anthropic",
            "model_b_model": "claude-sonnet-4",
            "anthropic_key": "sk-ant-test",
        }
        assert validate_per_model_config("model_b", config) == []

    def test_valid_helper_agent_config(self):
        """Fully configured helper_agent returns no errors."""
        config = {
            "helper_agent_provider": "ollama",
            "helper_agent_model": "gemma3:4b",
        }
        assert validate_per_model_config("helper_agent", config) == []

    def test_missing_provider_returns_error(self):
        """No provider set for model_a."""
        config = {"model_a_model": "gpt-4o"}
        errors = validate_per_model_config("model_a", config)
        assert len(errors) >= 1
        assert any("provider" in e.lower() for e in errors)

    def test_missing_model_returns_error(self):
        """No model set for model_a."""
        config = {"model_a_provider": "openai", "openai_key": "sk-test"}
        errors = validate_per_model_config("model_a", config)
        assert len(errors) >= 1
        assert any("model" in e.lower() for e in errors)

    def test_both_missing_returns_two_errors(self):
        """Neither provider nor model set."""
        errors = validate_per_model_config("model_a", {})
        assert len(errors) >= 2

    def test_openai_provider_without_api_key_returns_error(self):
        """Openai provider but no api key."""
        config = {
            "model_a_provider": "openai",
            "model_a_model": "gpt-4o",
        }
        errors = validate_per_model_config("model_a", config)
        assert len(errors) >= 1

    def test_anthropic_provider_without_api_key_returns_error(self):
        """Anthropic provider but no api key."""
        config = {
            "model_b_provider": "anthropic",
            "model_b_model": "claude-sonnet-4",
        }
        errors = validate_per_model_config("model_b", config)
        assert len(errors) >= 1


class TestProviderTemperatureParam:
    """Tests that all 4 provider adapters accept the temperature parameter."""

    @pytest.mark.parametrize("provider_class,name,cfg", [
        (OllamaProvider, "ollama", {}),
        (OpenAIProvider, "openai", {"openai_key": "sk-test"}),
        (AnthropicProvider, "anthropic", {"anthropic_key": "sk-ant-test"}),
        (VLLMProvider, "vllm", {"vllm_url": "http://localhost:8001/v1"}),
    ])
    def test_predict_accepts_temperature_param(self, provider_class, name, cfg):
        """predict() accepts temperature parameter without error (signature check, not invocation)."""
        import inspect
        sig = inspect.signature(provider_class(cfg).predict)
        assert "temperature" in sig.parameters
        assert sig.parameters["temperature"].default == 0.7
