"""LLM provider adapters and dispatch logic.

Moved from main.py during root reorganization (Step 3).
Each adapter wraps a different LLM backend behind a common interface.

The hexagonal architecture port is defined by ``LLMProviderPort`` protocol:
all adapters implement the same ``predict()`` and ``chat()`` signatures,
making them interchangeable at the dispatch point.

Import from this module:
    from services.llm_providers import (
        get_provider, _derive_provider, validate_provider_config, predict_llm,
    )
"""
from typing import Protocol, runtime_checkable
from services.prediction import build_prediction_prompt, build_absa_models


@runtime_checkable
class LLMProviderPort(Protocol):
    """Port for LLM provider adapters (hexagonal architecture).

    All provider adapters implement this protocol, making them
    interchangeable at the dispatch point. The protocol defines
    two operations:

    - ``predict()``: structured ABSA triplet prediction with
      Pydantic response parsing.
    - ``chat()``: free-form conversational response for the
      Helper Agent panel.
    """

    def predict(self, text, considered_sentiment_elements, examples,
                aspect_categories, polarities, allow_implicit_aspect_terms,
                allow_implicit_opinion_terms, n_few_shot, llm_model,
                prompt_template=None):
        """Predict ABSA triplets from text.

        Returns (predictions_dict, few_shot_examples_list).
        """
        ...

    def chat(self, messages, model, temperature=0.7, max_tokens=300):
        """Send a chat message and return the response text."""
        ...

def predict_llm(text, considered_sentiment_elements, examples, aspect_categories, polarities, allow_implicit_aspect_terms=False, allow_implicit_opinion_terms=False, n_few_shot=10, llm_model="gemma3:4b", prompt_template=None):
    """Predict sentiment elements using Ollama (backward-compatible wrapper).

    Stable compatibility shim for eval.py — delegates to the provider adapter
    pattern. Defaults to Ollama for backward compatibility; accepts an optional
    provider_config dict to route through any configured provider.

    This is the entry point for the LLM prediction port. All provider
    communication flows through this function (or the underlying adapter
    classes), making it the stable boundary in the hexagonal architecture.
    """
    provider = OllamaProvider({})
    result, examples = provider.predict(
        text, considered_sentiment_elements, examples,
        aspect_categories, polarities,
        allow_implicit_aspect_terms, allow_implicit_opinion_terms,
        n_few_shot, llm_model, prompt_template=prompt_template,
    )
    return result, examples

class OllamaProvider:
    """LLM provider adapter for Ollama (local inference).

    Uses the ollama Python library for both structured ABSA prediction
    (via Pydantic JSON schema) and general chat. Requires a running
    Ollama server (default: localhost:11434).
    """

    def __init__(self, config: dict):
        """Initialize with the application config dict (CONFIG_DATA)."""
        self.config = config

    def predict(self, text, considered_sentiment_elements, examples, aspect_categories, polarities, allow_implicit_aspect_terms, allow_implicit_opinion_terms, n_few_shot, llm_model, prompt_template=None):
        """Predict ABSA triplets via Ollama's generate endpoint with structured JSON output.

        Uses Pydantic model_json_schema() for the format parameter,
        ensuring the model returns valid structured data conforming to
        the expected aspect schema.
        """
        from ollama import generate
        import json

        prompt, few_shot_examples = build_prediction_prompt(
            text, considered_sentiment_elements, examples,
            aspect_categories, polarities,
            allow_implicit_aspect_terms, allow_implicit_opinion_terms, n_few_shot,
            prompt_template=prompt_template
        )
        Aspects, _, _ = build_absa_models(
            text, considered_sentiment_elements, polarities,
            aspect_categories, allow_implicit_aspect_terms, allow_implicit_opinion_terms
        )

        response = generate(
            prompt=prompt,
            model=llm_model,
            raw=True,
            options={"temperature": 0.0, "max_tokens": 1024},
            format=Aspects.model_json_schema()
        )
        aspects = Aspects.model_validate_json(response.response)
        if not aspects.aspects:
            return {"aspects": []}, few_shot_examples
        return json.loads(response.response), few_shot_examples

    def chat(self, messages, model, temperature=0.7, max_tokens=300):
        """Send a chat message via Ollama's chat endpoint.

        Uses ollama.chat() for general-purpose conversation (not structured output).
        Used by the Helper Agent panel (POST /agent/chat).

        Args:
            messages: List of dicts with 'role' and 'content' keys.
            model: Ollama model name (e.g. 'gemma3:4b').
            temperature: Sampling temperature (default 0.7).
            max_tokens: Max tokens in response (default 300).

        Returns:
            str: The model's response text.
        """
        from ollama import chat as ollama_chat
        response = ollama_chat(
            model=model,
            messages=messages,
            options={"temperature": temperature, "max_tokens": max_tokens}
        )
        return response["message"]["content"]



class OpenAIProvider:
    """LLM provider adapter for OpenAI-compatible APIs.

    Uses the official openai Python library with structured output via
    beta.chat.completions.parse (Pydantic response_format). Also supports
    standard chat completions for the Helper Agent panel.

    Requires 'openai_key' in the config dict.
    """

    def __init__(self, config: dict):
        """Initialize with the application config dict (CONFIG_DATA)."""
        self.config = config

    def predict(self, text, considered_sentiment_elements, examples, aspect_categories, polarities, allow_implicit_aspect_terms, allow_implicit_opinion_terms, n_few_shot, llm_model, prompt_template=None):
        """Predict ABSA triplets via OpenAI structured output (beta.parse).

        Uses client.beta.chat.completions.parse with a Pydantic response_format
        to get validated, structured triplet data directly from the API.
        """
        from openai import OpenAI
        import json

        openai_key = self.config.get("openai_key")
        if not openai_key:
            raise ValueError("OpenAI API key is required")

        client = OpenAI(api_key=openai_key)
        prompt, few_shot_examples = build_prediction_prompt(
            text, considered_sentiment_elements, examples,
            aspect_categories, polarities,
            allow_implicit_aspect_terms, allow_implicit_opinion_terms, n_few_shot,
            prompt_template=prompt_template
        )
        Aspects, _, _ = build_absa_models(
            text, considered_sentiment_elements, polarities,
            aspect_categories, allow_implicit_aspect_terms, allow_implicit_opinion_terms
        )

        try:
            completion = client.beta.chat.completions.parse(
                model=llm_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant for aspect-based sentiment analysis. Extract the sentiment elements from the given text according to the provided instructions."},
                    {"role": "user", "content": prompt},
                ],
                response_format=Aspects,
                temperature=0.0
            )
            message = completion.choices[0].message
            if message.parsed:
                aspects_data = {"aspects": []}
                for aspect in message.parsed.aspects:
                    aspect_dict = {}
                    for element in considered_sentiment_elements:
                        aspect_dict[element] = getattr(aspect, element).value
                    aspects_data["aspects"].append(aspect_dict)
                return aspects_data, few_shot_examples
            else:
                print(f"OpenAI refused the request: {message.refusal}")
                return {"aspects": []}, few_shot_examples
        except Exception as e:
            print(f"Error in OpenAI prediction: {e}")
            return {"aspects": []}, few_shot_examples

    def chat(self, messages, model, temperature=0.7, max_tokens=300):
        """Send a chat message via OpenAI chat completions.

        Uses client.chat.completions.create for general conversation.
        Used by the Helper Agent panel.

        Args:
            messages: List of dicts with 'role' and 'content'.
            model: OpenAI model name (e.g. 'gpt-4o-2024-08-06').
            temperature: Sampling temperature (default 0.7).
            max_tokens: Max response tokens (default 300).

        Returns:
            str: The model's response text.
        """
        from openai import OpenAI
        openai_key = self.config.get("openai_key")
        if not openai_key:
            raise ValueError("OpenAI API key is required for chat")
        client = OpenAI(api_key=openai_key)
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return completion.choices[0].message.content


class AnthropicProvider:

    """LLM provider adapter for Anthropic (Claude).

    Uses the anthropic Python library with messages.create for both
    ABSA prediction (JSON extraction from response text) and general
    chat (OpenAI→Anthropic message format conversion).

    Requires 'anthropic_key' in the config dict.
    """

    def __init__(self, config: dict):
        """Initialize with the application config dict (CONFIG_DATA)."""
        self.config = config

    def predict(self, text, considered_sentiment_elements, examples, aspect_categories, polarities, allow_implicit_aspect_terms, allow_implicit_opinion_terms, n_few_shot, llm_model, prompt_template=None):
        """Predict ABSA triplets via Anthropic Claude.

        Sends the prompt as a user message, then parses JSON from the
        response content. Unlike OpenAI's structured output, this requires
        manual JSON extraction from the response text.
        """
        from anthropic import Anthropic
        import json

        anthropic_key = self.config.get("anthropic_key")
        if not anthropic_key:
            raise ValueError("Anthropic API key is required")

        client = Anthropic(api_key=anthropic_key)

        prompt, few_shot_examples = build_prediction_prompt(
            text, considered_sentiment_elements, examples,
            aspect_categories, polarities,
            allow_implicit_aspect_terms, allow_implicit_opinion_terms, n_few_shot,
            prompt_template=prompt_template
        )
        Aspects, _, _ = build_absa_models(
            text, considered_sentiment_elements, polarities,
            aspect_categories, allow_implicit_aspect_terms, allow_implicit_opinion_terms
        )

        try:
            response = client.messages.create(
                model=llm_model or "claude-sonnet-4-20250514",
                max_tokens=1024,
                temperature=0.0,
                system="You are a helpful assistant for aspect-based sentiment analysis. Extract the sentiment elements from the given text according to the provided instructions. Return valid JSON matching the expected schema.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            content = response.content[0].text if response.content else "{}"
            # Extract JSON from the response
            parsed = json.loads(content)
            aspects_list = parsed.get("aspects", [])
            return {"aspects": aspects_list}, few_shot_examples
        except Exception as e:
            print(f"Error in Anthropic prediction: {e}")
            return {"aspects": []}, few_shot_examples

    def chat(self, messages, model, temperature=0.7, max_tokens=300):
        """Send a chat message via Anthropic Claude.

        Converts OpenAI-style message format (system + user/assistant roles)
        to Anthropic's format (system string + messages list without system role).
        Used by the Helper Agent panel.

        Args:
            messages: OpenAI-format message list with 'role' and 'content'.
            model: Anthropic model (e.g. 'claude-sonnet-4-20250514').
            temperature: Sampling temperature (default 0.7).
            max_tokens: Max response tokens (default 300).

        Returns:
            str: The model's response text.
        """
        from anthropic import Anthropic
        anthropic_key = self.config.get("anthropic_key")
        if not anthropic_key:
            raise ValueError("Anthropic API key is required for chat")
        client = Anthropic(api_key=anthropic_key)

        # Convert OpenAI-style messages to Anthropic format
        system_content = None
        anthropic_messages = []
        for m in messages:
            if m["role"] == "system":
                system_content = m["content"]
            else:
                anthropic_messages.append({"role": m["role"], "content": m["content"]})

        response = client.messages.create(
            model=model or "claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_content,
            messages=anthropic_messages if anthropic_messages else [{"role": "user", "content": "Hello"}]
        )
        return response.content[0].text


class VLLMProvider:

    """LLM provider adapter for vLLM (OpenAI-compatible API).

    Uses the openai Python library with a custom base_url pointing to the
    vLLM server. Since vLLM does not support beta.chat.completions.parse
    (structured output), prediction uses standard completions + manual JSON parse.

    Requires 'vllm_url' in the config dict (e.g. 'http://localhost:8001/v1').
    """

    def __init__(self, config: dict):
        """Initialize with the application config dict (CONFIG_DATA)."""
        self.config = config

    def predict(self, text, considered_sentiment_elements, examples, aspect_categories, polarities, allow_implicit_aspect_terms, allow_implicit_opinion_terms, n_few_shot, llm_model, prompt_template=None):
        """Predict ABSA triplets via vLLM (standard OpenAI completion + manual JSON parse).

        vLLM does not support the structured output API (beta.parse), so this
        uses a standard chat completion and attempts to parse JSON from the
        response text.
        """
        from openai import OpenAI
        import json

        vllm_url = self.config.get("vllm_url")
        if not vllm_url:
            raise ValueError("vLLM URL is required")

        client = OpenAI(api_key="EMPTY", base_url=vllm_url)

        prompt, few_shot_examples = build_prediction_prompt(
            text, considered_sentiment_elements, examples,
            aspect_categories, polarities,
            allow_implicit_aspect_terms, allow_implicit_opinion_terms, n_few_shot,
            prompt_template=prompt_template
        )
        Aspects, _, _ = build_absa_models(
            text, considered_sentiment_elements, polarities,
            aspect_categories, allow_implicit_aspect_terms, allow_implicit_opinion_terms
        )

        # vLLM may not support beta.chat.completions.parse, so use standard completion + manual parse
        try:
            completion = client.chat.completions.create(
                model=llm_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant for aspect-based sentiment analysis. Extract the sentiment elements from the given text according to the provided instructions. Return valid JSON matching the expected schema."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=1024
            )
            content = completion.choices[0].message.content
            try:
                parsed = json.loads(content)
                aspects_list = parsed.get("aspects", [])
                return {"aspects": aspects_list}, few_shot_examples
            except json.JSONDecodeError:
                print(f"vLLM returned non-JSON response: {content[:200]}")
                return {"aspects": []}, few_shot_examples
        except Exception as e:
            print(f"Error in vLLM prediction: {e}")
            return {"aspects": []}, few_shot_examples

    def chat(self, messages, model, temperature=0.7, max_tokens=300):
        """Send a chat message via vLLM (OpenAI-compatible API).

        Uses the openai Python library with the vLLM base_url for general
        conversation. Used by the Helper Agent panel.

        Args:
            messages: List of dicts with 'role' and 'content'.
            model: vLLM model name.
            temperature: Sampling temperature (default 0.7).
            max_tokens: Max response tokens (default 300).

        Returns:
            str: The model's response text.
        """
        from openai import OpenAI
        vllm_url = self.config.get("vllm_url")
        if not vllm_url:
            raise ValueError("vLLM URL is required")
        client = OpenAI(api_key="EMPTY", base_url=vllm_url)
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return completion.choices[0].message.content


# Provider registry: maps provider name → adapter class

PROVIDER_REGISTRY = {
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "vllm": VLLMProvider,
}


def _derive_provider(config: dict) -> str:
    """Derive the LLM provider from a config dict.

    Priority:
    1. Explicit 'llm_provider' key → use it directly.
    2. Exactly one of (openai_key, anthropic_key, vllm_url) is set → derive to that provider.
    3. Multiple of the above are set but no explicit 'llm_provider' → raise ValueError.
    4. None are set → fall back to 'ollama'.

    NOTE: The validation step (checking that the chosen provider has its required
    config keys) is handled by ``validate_provider_config()`` in this same module.
    Call it after ``_derive_provider()`` to ensure the provider can actually run.
    """
    explicit = config.get('llm_provider')
    if explicit:
        return explicit

    configured = [
        name for name, key in [
            ("openai", "openai_key"),
            ("anthropic", "anthropic_key"),
            ("vllm", "vllm_url"),
        ] if config.get(key)
    ]

    if len(configured) > 1:
        raise ValueError(
            f"Multiple providers configured ({', '.join(configured)}) "
            f"but no --llm-provider specified. Pick one explicitly."
        )
    elif len(configured) == 1:
        return configured[0]
    else:
        return "ollama"


def get_provider(provider_name: str, config: dict):
    """Factory: instantiate the right provider adapter for the given name.

    Args:
        provider_name: One of 'ollama', 'openai', 'anthropic', 'vllm'.
        config: Configuration dict (CONFIG_DATA) containing provider-specific keys.

    Returns:
        An instance of the corresponding provider adapter class.

    Raises:
        ValueError: If provider_name is unknown.
    """
    provider_name = provider_name.lower().strip()
    if provider_name not in PROVIDER_REGISTRY:
        raise ValueError(
            f"Unknown LLM provider '{provider_name}'. "
            f"Available: {', '.join(PROVIDER_REGISTRY.keys())}"
        )
    return PROVIDER_REGISTRY[provider_name](config)


def validate_provider_config(provider_name: str, config: dict) -> list[str]:
    """Validate that the given LLM provider has its required config keys.

    Checks provider-specific requirements:
    - openai → openai_key must be set
    - anthropic → anthropic_key must be set
    - vllm → vllm_url must be set
    - ollama → no required keys (runs locally, no validation needed)

    Returns a list of error messages (empty list = valid).
    Each caller handles dispatch differently:
    - cli.py: sys.exit(1) on any error
    - main.py endpoints: raises HTTPException(400)
    """
    errors = []
    if provider_name == 'openai' and not config.get('openai_key'):
        errors.append(
            "OpenAI provider selected but no API key configured. Use --openai-key."
        )
    if provider_name == 'anthropic' and not config.get('anthropic_key'):
        errors.append(
            "Anthropic provider selected but no API key configured. Use --anthropic-key."
        )
    if provider_name == 'vllm' and not config.get('vllm_url'):
        errors.append(
            "vLLM provider selected but no URL configured. Use --vllm-url."
        )
    return errors


