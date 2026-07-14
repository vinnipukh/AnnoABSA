"""Global state and configuration for AnnoABSA."""
import os
import json
from services.prediction import DEFAULT_LABELING_TEMPLATE, DEFAULT_CHAT_TEMPLATE

# Global variable to store the data file path and type
DATA_FILE_PATH = os.environ.get('ABSA_DATA_PATH', "annotations.csv")  # Default
DATA_FILE_TYPE = "json" if DATA_FILE_PATH.endswith('.json') else "csv"
CONFIG_PATH = os.environ.get('ABSA_CONFIG_PATH', None)  # Path to config file
CONFIG_DATA = {}  # Store configuration data including session_id

# Load configuration if provided
CONFIG_PATH = os.environ.get('ABSA_CONFIG_PATH')
if CONFIG_PATH and os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            CONFIG_DATA = json.load(f)
    except Exception as e:
        print(f"Warning: Could not load config from {CONFIG_PATH}: {e}")

# Get auto_positions flag from loaded configuration
AUTO_POSITIONS = CONFIG_DATA.get('auto_positions', False)


def set_data_file(file_path: str):
    """Set the data file path and determine the file type from its extension.

    Updates the global DATA_FILE_PATH and DATA_FILE_TYPE.
    Called:
    - From cli.py at startup (via config-based file selection)
    - From upload_data endpoint when a user uploads a file through the UI

    Args:
        file_path: Absolute or relative path to a CSV or JSON file.
    """
    global DATA_FILE_PATH, DATA_FILE_TYPE
    DATA_FILE_PATH = file_path
    DATA_FILE_TYPE = "json" if file_path.endswith('.json') else "csv"


def set_config_file(config_path: str):
    """Set the path to the JSON configuration file.

    Updates the global CONFIG_PATH. The config is loaded on the next
    call to load_config() or on the next request that reads configuration.

    Args:
        config_path: Path to a .json config file.
    """
    global CONFIG_PATH
    CONFIG_PATH = config_path


def load_config():
    """Load configuration from JSON file."""
    if CONFIG_PATH and os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    # Return default configuration if no config file
    return {
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
        "enable_pre_prediction": False,
        "disable_ai_automatic_prediction": False,
        "enable_helper_agent": True,
        "llm_provider": "ollama",
        "llm_model": "gemma3:4b",
        "openai_key": None,
        "anthropic_key": None,
        "vllm_url": None,
        "vllm_model": None,
        "compare_model_a_csv": None,
        "compare_model_a_name": None,
        "compare_model_b_csv": None,
        "compare_model_b_name": None,
        "labeling_prompt_template": DEFAULT_LABELING_TEMPLATE,
        "helper_agent_prompt_template": DEFAULT_CHAT_TEMPLATE,
        "theme": "dark",
        # Phase 4: Live Compare Mode config
        "compare_mode": "4way",
        "model_a_provider": None,
        "model_a_model": None,
        "model_a_prompt": DEFAULT_LABELING_TEMPLATE,
        "model_a_temperature": 0.7,
        "model_b_provider": None,
        "model_b_model": None,
        "model_b_prompt": DEFAULT_LABELING_TEMPLATE,
        "model_b_temperature": 0.7,
        "helper_agent_provider": None,
        "helper_agent_model": None,
        "helper_agent_prompt": DEFAULT_CHAT_TEMPLATE,
        "helper_agent_temperature": 0.7,
        # Phase 5: configurable keyboard shortcut
        "ai_shortcut_key": "a",
    }


def set_config(config_dict: dict):
    """Set the configuration data including session_id."""
    global CONFIG_DATA
    CONFIG_DATA = config_dict
