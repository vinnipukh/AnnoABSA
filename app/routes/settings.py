"""Settings endpoints — GET and PATCH configuration."""
from fastapi import APIRouter, HTTPException
import json
from app.config import CONFIG_DATA, CONFIG_PATH
from app.data import get_total_count, get_current_index, max_number_of_idxs

router = APIRouter(tags=["settings"])


@router.get("/settings")
def get_settings():
    """Return annotation config + metadata (acts as de facto health check).

    Returns sentiment elements, categories, polarities, boolean flags,
    current_index, max_number_of_idxs, and session_id.
    Called by the frontend on every page load.
    """
    settings = {
        "sentiment elements": CONFIG_DATA.get("sentiment_elements", ["aspect_term", "aspect_category", "sentiment_polarity", "opinion_term"]),
        "total_count": get_total_count(),
        "sentiment_polarity options": CONFIG_DATA.get("sentiment_polarity_options", ["positive", "negative", "neutral"]),
        "aspect_categories": CONFIG_DATA.get("aspect_categories", ['location general', 'food prices', 'food quality', 'food general',
                                                                   'ambience general', 'service general', 'restaurant prices',
                                                                   'drinks prices', 'restaurant miscellaneous', 'drinks quality',
                                                                   'drinks style_options', 'restaurant general', 'food style_options']),
        "implicit_aspect_term_allowed": CONFIG_DATA.get("implicit_aspect_term_allowed", True),
        "implicit_opinion_term_allowed": CONFIG_DATA.get("implicit_opinion_term_allowed", False),
        "auto_clean_phrases": CONFIG_DATA.get("auto_clean_phrases", True),
        "save_phrase_positions": CONFIG_DATA.get("save_phrase_positions", True),
        "click_on_token": CONFIG_DATA.get("click_on_token", True),
        "enable_pre_prediction": CONFIG_DATA.get("enable_pre_prediction", CONFIG_DATA.get("enable_preprediction", False)),
        "disable_ai_automatic_prediction": CONFIG_DATA.get("disable_ai_automatic_prediction", False),
        "enable_helper_agent": CONFIG_DATA.get("enable_helper_agent", True),
        "annotation_guideline": CONFIG_DATA.get("annotation_guideline", None),
        "theme": CONFIG_DATA.get("theme", "dark"),
        "llm_provider": CONFIG_DATA.get("llm_provider", "ollama"),
        "llm_model": CONFIG_DATA.get("llm_model", "gemma3:4b"),
        "vllm_model": CONFIG_DATA.get("vllm_model", None),
        "vllm_url": CONFIG_DATA.get("vllm_url", None),
        "n_few_shot": CONFIG_DATA.get("n_few_shot", 10),
        "compare_model_a_name": CONFIG_DATA.get("compare_model_a_name", None),
        "compare_model_b_name": CONFIG_DATA.get("compare_model_b_name", None),
        # Phase 4: Live Compare Mode settings
        "compare_mode": CONFIG_DATA.get("compare_mode", "csv"),
        "model_a_provider": CONFIG_DATA.get("model_a_provider", None),
        "model_a_model": CONFIG_DATA.get("model_a_model", None),
        "model_a_prompt": CONFIG_DATA.get("model_a_prompt", None),
        "model_a_temperature": CONFIG_DATA.get("model_a_temperature", 0.7),
        "model_b_provider": CONFIG_DATA.get("model_b_provider", None),
        "model_b_model": CONFIG_DATA.get("model_b_model", None),
        "model_b_prompt": CONFIG_DATA.get("model_b_prompt", None),
        "model_b_temperature": CONFIG_DATA.get("model_b_temperature", 0.7),
        "helper_agent_provider": CONFIG_DATA.get("helper_agent_provider", None),
        "helper_agent_model": CONFIG_DATA.get("helper_agent_model", None),
        "helper_agent_prompt": CONFIG_DATA.get("helper_agent_prompt", None),
        "helper_agent_temperature": CONFIG_DATA.get("helper_agent_temperature", 0.7),
        "ai_shortcut_key": CONFIG_DATA.get("ai_shortcut_key", "a"),
        "current_index": get_current_index(),
        "max_number_of_idxs": max_number_of_idxs()
    }

    # Add session_id if it exists
    if CONFIG_DATA.get("session_id"):
        settings["session_id"] = CONFIG_DATA["session_id"]

    return settings


@router.patch("/settings")
def update_settings(updates: dict):
    """Merge updates into CONFIG_DATA and persist to config JSON file.

    Accepts a JSON body with one or more config key-value pairs.
    Changes take effect immediately in-memory and are persisted to disk.
    Does NOT re-instantiate providers or reload comparison CSVs.

    Args:
        updates: Dict of config key-value pairs to update.

    Returns:
        {"status": "ok"}
    """
    global CONFIG_DATA  # noqa: PLW0603
    try:
        # Merge updates into the in-memory config
        for key, value in updates.items():
            CONFIG_DATA[key] = value

        # Persist to config JSON file if a path is configured
        if CONFIG_PATH:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(CONFIG_DATA, f, indent=2, ensure_ascii=False)

        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error updating settings: {str(e)}")
