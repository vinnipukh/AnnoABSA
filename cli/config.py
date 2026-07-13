"""Configuration management for AnnoABSA CLI."""

import json
import sys
import os
from typing import Dict, Any, List

# ── Prompt template defaults (imported from services to avoid duplication) ──
from services.prediction import DEFAULT_LABELING_TEMPLATE as CLI_DEFAULT_LABELING_TEMPLATE
from services.prediction import DEFAULT_CHAT_TEMPLATE as CLI_DEFAULT_CHAT_TEMPLATE


class ABSAAnnotatorConfig:
    """Configuration manager for AnnoABSA."""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.config = {
            "csv_path": csv_path,
            "session_id": None,
            "sentiment_elements": ["aspect_term", "aspect_category", "sentiment_polarity", "opinion_term"],
            "sentiment_polarity_options": ["positive", "negative", "neutral"],
            "aspect_categories": [
                'location general', 'food prices', 'food quality', 'food general',
                'ambience general', 'service general', 'restaurant prices',
                'drinks prices', 'restaurant miscellaneous', 'drinks quality',
                'drinks style_options', 'restaurant general', 'food style_options'
            ],
            "implicit_aspect_term_allowed": True,
            "implicit_opinion_term_allowed": False,
            "auto_clean_phrases": True,
            "save_phrase_positions": True,
            "click_on_token": True,
            "auto_positions": False,
            "store_time": False,
            "display_avg_annotation_time": False,
            "enable_pre_prediction": False,
            "disable_ai_automatic_prediction": False,
            "annotation_guideline": None,
            "n_few_shot": 10,
            "llm_provider": None,
            "llm_model": "gemma3:4b",
            "openai_key": None,
            "anthropic_key": None,
            "vllm_url": None,
            "vllm_model": None,
            "compare_model_a_csv": None,
            "compare_model_a_name": None,
            "compare_model_b_csv": None,
            "compare_model_b_name": None,
            "labeling_prompt_template": CLI_DEFAULT_LABELING_TEMPLATE,
            "helper_agent_prompt_template": CLI_DEFAULT_CHAT_TEMPLATE,
            # Phase 4: Live Compare Mode defaults
            "compare_mode": "csv",
            "model_a_provider": None,
            "model_a_model": None,
            "model_a_prompt": CLI_DEFAULT_LABELING_TEMPLATE,
            "model_a_temperature": 0.7,
            "model_b_provider": None,
            "model_b_model": None,
            "model_b_prompt": CLI_DEFAULT_LABELING_TEMPLATE,
            "model_b_temperature": 0.7,
            "helper_agent_provider": None,
            "helper_agent_model": None,
            "helper_agent_prompt": CLI_DEFAULT_CHAT_TEMPLATE,
            "helper_agent_temperature": 0.7,
        }

    def set_sentiment_elements(self, elements: List[str]) -> None:
        """Set the sentiment elements to annotate."""
        valid_elements = ["aspect_term", "aspect_category",
                          "sentiment_polarity", "opinion_term"]
        for element in elements:
            if element not in valid_elements:
                raise ValueError(
                    f"Invalid sentiment element: {element}. Valid options: {valid_elements}")
        self.config["sentiment_elements"] = elements

    def set_sentiment_polarities(self, polarities: List[str]) -> None:
        """Set the available sentiment polarities."""
        self.config["sentiment_polarity_options"] = polarities

    def set_aspect_categories(self, categories: List[str]) -> None:
        """Set the available aspect categories."""
        self.config["aspect_categories"] = categories

    def set_implicit_aspect_allowed(self, allowed: bool) -> None:
        """Set whether implicit aspect terms are allowed."""
        self.config["implicit_aspect_term_allowed"] = allowed

    def set_implicit_opinion_allowed(self, allowed: bool) -> None:
        """Set whether implicit opinion terms are allowed."""
        self.config["implicit_opinion_term_allowed"] = allowed

    def set_auto_clean_phrases(self, enabled: bool) -> None:
        """Set whether automatic phrase cleaning is enabled."""
        self.config["auto_clean_phrases"] = enabled

    def set_save_phrase_positions(self, enabled: bool) -> None:
        """Set whether phrase start/end positions are saved (at_start, at_end, ot_start, ot_end)."""
        self.config["save_phrase_positions"] = enabled

    def set_click_on_token(self, enabled: bool) -> None:
        """Set whether click-on-token feature is enabled (snap to token boundaries)."""
        self.config["click_on_token"] = enabled

    def set_auto_positions(self, enabled: bool) -> None:
        """Set whether automatic position data filling is enabled for existing phrases on startup."""
        self.config["auto_positions"] = enabled

    def set_store_time(self, enabled: bool) -> None:
        """Set whether timing data should be stored (duration and change status for each annotation session)."""
        self.config["store_time"] = enabled

    def set_display_avg_annotation_time(self, enabled: bool) -> None:
        """Set whether average annotation time should be displayed."""
        self.config["display_avg_annotation_time"] = enabled

    def set_enable_pre_prediction(self, enabled: bool) -> None:
        """Set whether AI pre-prediction is enabled."""
        self.config["enable_pre_prediction"] = enabled

    def set_disable_ai_automatic_prediction(self, disabled: bool) -> None:
        """Set whether automatic AI prediction triggering is disabled."""
        self.config["disable_ai_automatic_prediction"] = disabled

    def set_annotation_guideline(self, guideline_path: str) -> None:
        """Set the path to the annotation guideline PDF file and encode it as base64."""
        if guideline_path and not os.path.exists(guideline_path):
            raise ValueError(
                f"Annotation guideline file not found: {guideline_path}")

        if guideline_path:
            # Read and encode PDF as base64
            import base64
            with open(guideline_path, 'rb') as pdf_file:
                pdf_data = pdf_file.read()
                encoded_pdf = base64.b64encode(pdf_data).decode('utf-8')
                self.config["annotation_guideline"] = f"data:application/pdf;base64,{encoded_pdf}"
        else:
            self.config["annotation_guideline"] = None

    def set_openai_key(self, openai_key: str) -> None:
        """Set the OpenAI API key for using OpenAI models."""
        self.config["openai_key"] = openai_key

    def set_n_few_shot(self, n_few_shot: int) -> None:
        """Set the maximum number of few-shot examples to include in LLM prompts."""
        if n_few_shot < 0:
            raise ValueError("Number of few-shot examples must be non-negative")
        self.config["n_few_shot"] = n_few_shot

    def set_llm_provider(self, provider: str) -> None:
        """Set the LLM provider (openai, ollama, anthropic, vllm)."""
        valid = ["openai", "ollama", "anthropic", "vllm"]
        provider = provider.lower().strip()
        if provider not in valid:
            raise ValueError(f"Invalid LLM provider: {provider}. Valid options: {valid}")
        self.config["llm_provider"] = provider

    def set_llm_model(self, model: str) -> None:
        """Set the LLM model name."""
        self.config["llm_model"] = model

    def set_anthropic_key(self, anthropic_key: str) -> None:
        """Set the Anthropic API key."""
        self.config["anthropic_key"] = anthropic_key

    def set_vllm_url(self, vllm_url: str) -> None:
        """Set the vLLM server base URL."""
        self.config["vllm_url"] = vllm_url

    def set_vllm_model(self, vllm_model: str) -> None:
        """Set the vLLM model name."""
        self.config["vllm_model"] = vllm_model

    def set_compare_model_a_csv(self, csv_path: str) -> None:
        """Set the CSV path for comparison Model A."""
        self.config["compare_model_a_csv"] = csv_path

    def set_compare_model_a_name(self, name: str) -> None:
        """Set the display name for comparison Model A."""
        self.config["compare_model_a_name"] = name

    def set_compare_model_b_csv(self, csv_path: str) -> None:
        """Set the CSV path for comparison Model B."""
        self.config["compare_model_b_csv"] = csv_path

    def set_compare_model_b_name(self, name: str) -> None:
        """Set the display name for comparison Model B."""
        self.config["compare_model_b_name"] = name

    def set_session_id(self, session_id: str) -> None:
        """Set the session ID for this annotation session."""
        self.config["session_id"] = session_id

    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration."""
        return self.config.copy()

    def save_config(self, output_path: str = "absa_config.json") -> None:
        """Save configuration to JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        print(f"✅ Configuration saved to {output_path}")

    def load_config(self, config_path: str) -> None:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)

            # Update configuration with loaded values
            for key, value in loaded_config.items():
                if key in self.config:
                    self.config[key] = value

            print(f"✅ Configuration loaded from {config_path}")

        except FileNotFoundError:
            print(f"❌ Configuration file '{config_path}' not found!")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in configuration file: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error loading configuration: {e}")
            sys.exit(1)

    def print_config(self) -> None:
        """Print the current configuration in a formatted way."""
        print("🎯 ABSA Annotator Configuration")
        print("=" * 40)
        print(f"📄 Data Path: {self.config['csv_path']}")
        if self.config.get('session_id'):
            print(f"🔖 Session ID: {self.config['session_id']}")
        print(
            f"🏷️  Sentiment Elements: {', '.join(self.config['sentiment_elements'])}")
        print(
            f"😊 Sentiment Polarities: {', '.join(self.config['sentiment_polarity_options'])}")
        print(
            f"📝 Aspect Categories: {len(self.config['aspect_categories'])} categories")
        print(
            f"🔍 Implicit Aspect terms: {'✅' if self.config['implicit_aspect_term_allowed'] else '❌'}")
        print(
            f"💭 Implicit Opinion terms: {'✅' if self.config['implicit_opinion_term_allowed'] else '❌'}")
        print(f"🔧 Auto-add Positions: {'✅' if self.config['auto_positions'] else '❌'}")
        print(f"🎯 Few-shot Examples: {self.config['n_few_shot']}")
        provider = self.config.get('llm_provider', 'ollama')
        model = self.config.get('llm_model', 'gemma3:4b')
        print(f"🤖 LLM Provider: {provider} (model: {model})")
        if provider == 'openai' and self.config.get('openai_key'):
            print(f"   🔑 OpenAI key: configured")
        elif provider == 'anthropic' and self.config.get('anthropic_key'):
            print(f"   🔑 Anthropic key: configured")
        elif provider == 'vllm' and self.config.get('vllm_url'):
            vllm_model = self.config.get('vllm_model') or model
            print(f"   🔗 vLLM URL: {self.config['vllm_url']} (model: {vllm_model})")
