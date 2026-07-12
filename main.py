"""AnnoABSA FastAPI backend — application, endpoints, and data persistence."""
from app.config import *  # noqa: F401, F403 — re-export for backward compat (cli.py, tests)
from app.data import load_data, save_data, parse_triplet_column, _load_comparison_csv, get_total_count, get_current_index, max_number_of_idxs  # noqa: F401, E501
import re
import time
import numpy as np
try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import UploadFile, File
from pydantic import BaseModel
import pandas as pd
import json
import os
from fastapi import HTTPException
from models.schemas import SaveTripletsRequest, AgentChatRequest
from services.prediction import (
    DEFAULT_LABELING_TEMPLATE, DEFAULT_CHAT_TEMPLATE,
    generate_mock_reasoning, find_phrase_positions,
    get_most_similar_examples, find_valid_phrases_list,
    build_prediction_prompt, build_absa_models,
)
from services.llm_providers import (
    get_provider, _derive_provider, PROVIDER_REGISTRY,
)
from app.routes.nlp import router as nlp_router
import ast

app = FastAPI()

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
        "compare_mode": "csv",
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
    }


def set_config(config_dict: dict):
    """Set the configuration data including session_id."""
    global CONFIG_DATA
    CONFIG_DATA = config_dict


def load_data():
    """Load data from CSV or JSON file with UTF-8 encoding."""
    if DATA_FILE_TYPE == "json":
        with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return pd.read_csv(DATA_FILE_PATH, encoding='utf-8')


def save_data(data):
    """Save data to CSV or JSON file with UTF-8 encoding."""
    if DATA_FILE_TYPE == "json":
        with open(DATA_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    else:
        if isinstance(data, list):
            # Convert list of dicts to DataFrame
            df = pd.DataFrame(data)
        else:
            df = data
        df.to_csv(DATA_FILE_PATH, index=False, encoding='utf-8')


app.add_middleware(
    CORSMiddleware,
    # Allow all origins for flexibility with different IPs/ports
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nlp_router)




# GET Endpoint


@app.get("/settings")
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
        "current_index": get_current_index(),
        "max_number_of_idxs": max_number_of_idxs()
    }

    # Add session_id if it exists
    if CONFIG_DATA.get("session_id"):
        settings["session_id"] = CONFIG_DATA["session_id"]

    return settings


@app.patch("/settings")
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
    global CONFIG_DATA
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



def parse_triplet_column(raw_val, prefix="t"):
    """Parse a Python list-literal string into a list of triplet dicts.

    Handles multiple input formats:
    - STD tuples: ``[('term', 'CATEGORY', 'polarity'), ...]``
    - STD lists: ``[['term', 'CATEGORY', 'polarity'], ...]``
    - Dict format: ``[{'aspect_term': ..., 'aspect_category': ..., 'sentiment_polarity': ...}, ...]``
    - Empty values: ``None``, ``"nan"``, ``"None"``, ``"[]"``, ``""``

    Used by:
    - get_data() to parse inline comparison columns (aspect_triplets / new_triplets)
    - _load_comparison_csv() to parse STD-format comparison CSVs

    Args:
        raw_val: Raw cell value from a CSV (string, NaN, or None).
        prefix: Prefix for generated triplet IDs (e.g. 'ma' for Model A, 'mb' for Model B).

    Returns:
        List of dicts with keys: id, aspect_term, aspect_category, sentiment_polarity.
    """
    if raw_val is None or str(raw_val).strip() in ["", "nan", "None", "[]"]:
        return []
    try:
        parsed = ast.literal_eval(str(raw_val))
        res = []
        if isinstance(parsed, list):
            for i, item in enumerate(parsed):
                if isinstance(item, (list, tuple)) and len(item) >= 3:
                    term = str(item[0]) if item[0] else "NULL"
                    cat = str(item[1])
                    pol = str(item[2]).lower()
                    res.append({
                        "id": f"{prefix}_{i}",
                        "aspect_term": term,
                        "aspect_category": cat,
                        "sentiment_polarity": pol
                    })
                elif isinstance(item, dict):
                    term = str(item.get("aspect_term", item.get("term", ""))) or "NULL"
                    cat = str(item.get("aspect_category", item.get("category", "")))
                    pol = str(item.get("sentiment_polarity", item.get("polarity", ""))).lower()
                    res.append({
                        "id": f"{prefix}_{i}",
                        "aspect_term": term,
                        "aspect_category": cat,
                        "sentiment_polarity": pol
                    })
        return res
    except Exception as e:
        print("Parse error:", e)
        return []

def _load_comparison_csv(csv_path: str, data_idx: int, review_text: str, prefix: str) -> list:
    """Load triplets from a comparison CSV, auto-detecting format.

    Supports:
    - STD format (columns: review, triplet) — matched by review text
    - Per-row format (columns: review_id, aspect_term, aspect_category, sentiment_polarity) — matched by index
    """
    if not csv_path or not os.path.exists(csv_path):
        return []
    try:
        df = pd.read_csv(csv_path, encoding='utf-8')
    except Exception as e:
        print(f"Warning: Could not read comparison CSV '{csv_path}': {e}")
        return []

    # Auto-detect: STD format has 'review' and 'triplet' columns
    if 'review' in df.columns and 'triplet' in df.columns:
        # STD format — match by review text
        match = df[df['review'] == review_text]
        results = []
        for i, (_, r) in enumerate(match.iterrows()):
            triplets = parse_triplet_column(r.get('triplet'), prefix=f"{prefix}_{i}")
            results.extend(triplets)
        return results
    else:
        # Per-row format — match by review_id index
        if 'review_id' in df.columns:
            match = df[df['review_id'] == data_idx]
        else:
            return []
        results = []
        for i, (_, r) in enumerate(match.iterrows()):
            results.append({
                "id": f"{prefix}_{i}",
                "aspect_term": str(r.get("aspect_term", "")),
                "aspect_category": str(r.get("aspect_category", "")),
                "sentiment_polarity": str(r.get("sentiment_polarity", ""))
            })
        return results


@app.get("/data/{data_idx}")
def get_data(data_idx: int):
    """Return a single row's review text, label, and model comparison data.

    This is the primary data endpoint — the frontend calls it whenever the
    user navigates to a row. Handles JSON and CSV formats. Supports inline
    comparison columns and external comparison CSVs.

    Args:
        data_idx: 0-based row index.

    Returns:
        dict with keys: id, text, review_text, label, translation,
        aspect_category_list, model_a_triplets, model_b_triplets,
        model_a_name, model_b_name, agent_initial_reasoning.
    """
    try:
        data = load_data()
        if data_idx >= len(data) or data_idx < 0:
            raise HTTPException(status_code=404, detail="Index out of range")

        default_aspects = CONFIG_DATA.get("aspect_categories", ['Restaurant#general', 'Service#general', 'Service#speed', 'Food#quality', 'Food#prices', 'Food#style_options', 'Ambience#general', 'Location#general', 'Drinks#quality', 'Drinks#prices'])

        model_a_triplets = []
        model_b_triplets = []
        model_a_name = CONFIG_DATA.get("compare_model_a_name", "Model A")
        model_b_name = CONFIG_DATA.get("compare_model_b_name", "Model B")
        text_val = ""
        translation_val = ""
        label_val = ""
        aspects_val = default_aspects

        if DATA_FILE_TYPE == "json":
            item = data[data_idx]
            text_val = item.get("review_text", item.get("text", ""))
            translation_val = item.get("translation", "")
            lbl = item.get("label", [])
            label_val = json.dumps(lbl, ensure_ascii=False) if isinstance(lbl, list) else str(lbl if lbl is not None else "")
            aspects_val = item.get("aspect_category_list", default_aspects)
            model_a_triplets = item.get("model_a_triplets", [])
            model_b_triplets = item.get("model_b_triplets", [])
        else:
            df = data
            row = df.iloc[data_idx]
            row_dict = row.to_dict()
            for key, val in row_dict.items():
                if pd.isna(val) or (isinstance(val, float) and val in [float("inf"), float("-inf")]):
                    row_dict[key] = ""
            text_val = str(row_dict.get("review_text", row_dict.get("text", "")))
            translation_val = str(row_dict.get("translation", ""))
            label_val = str(row_dict.get("label", ""))
            raw_asp = row_dict.get("aspect_category_list", None)
            aspects_val = raw_asp if raw_asp else default_aspects

            # Support inline columns: aspect_triplets / new_triplets (backward compat)
            if "aspect_triplets" in row_dict:
                model_a_triplets = parse_triplet_column(row_dict.get("aspect_triplets"), prefix="ma")
            if "new_triplets" in row_dict:
                model_b_triplets = parse_triplet_column(row_dict.get("new_triplets"), prefix="mb")

            # Load comparison CSVs from config (overrides inline columns if both exist)
            comp_a_path = CONFIG_DATA.get("compare_model_a_csv")
            comp_b_path = CONFIG_DATA.get("compare_model_b_csv")
            if comp_a_path or comp_b_path:
                if comp_a_path:
                    model_a_triplets = _load_comparison_csv(comp_a_path, data_idx, text_val, "ma")
                if comp_b_path:
                    model_b_triplets = _load_comparison_csv(comp_b_path, data_idx, text_val, "mb")

        agent_initial_reasoning = str(row_dict.get("reasoning", "")) if DATA_FILE_TYPE != "json" and "reasoning" in row_dict else ""
        if not agent_initial_reasoning or agent_initial_reasoning in ["nan", "None", ""]:
            agent_initial_reasoning = generate_mock_reasoning(text_val, model_a_name, model_b_name, model_a_triplets, model_b_triplets)

        return {
            "id": data_idx,
            "text": text_val,
            "review_text": text_val,
            "label": label_val,
            "translation": translation_val,
            "aspect_category_list": aspects_val,
            "model_a_triplets": model_a_triplets,
            "model_b_triplets": model_b_triplets,
            "model_a_name": model_a_name,
            "model_b_name": model_b_name,
            "agent_initial_reasoning": agent_initial_reasoning
        }

    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"{DATA_FILE_PATH} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_total_count():
    """Return the total number of data items (reviews) in the current dataset.

    Returns:
        Total row/item count (int).

    Raises HTTPException (500) on read errors, (404) if file missing.
    """
    try:
        data = load_data()
        return len(data)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"{DATA_FILE_PATH} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_current_index():
    """Find the index of the first unannotated data item.

    For JSON: returns the first entry without a 'label' key.
    For CSV: returns the first row whose label column is empty/NaN.
    If all items are annotated, returns len(data) (the count, not a valid index).

    Used by:
    - get_settings() to report current_index to the frontend
    - The frontend to decide which row to display on initial load

    Returns:
        int: Index of the first unannotated item, or total count if all done.
    """
    try:
        data = load_data()
        if DATA_FILE_TYPE == "json":
            # Find first entry that doesn't have a "label" key (not annotated yet)
            for idx, item in enumerate(data):
                if 'label' not in item:
                    return idx
            return len(data)  # All entries have been annotated
        else:
            # CSV handling
            df = data
            for idx in range(len(df)):
                if pd.isna(df.iloc[idx]['label']) or df.iloc[idx]['label'] == "":
                    return idx
            return len(df)
    except FileNotFoundError:
        return 0
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def max_number_of_idxs():
    """Return the total number of data items (alias for get_total_count).

    Returns the maximum valid index + 1. Used by the frontend for pagination.

    Returns:
        int: Total number of data items.
    """
    try:
        data = load_data()
        return len(data)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"{DATA_FILE_PATH} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# POST Endpoint


# Timing-Logik: Speichere pro Beispiel eine Liste von {duration, change}


@app.post("/timing/{data_idx}")
def post_timing(data_idx: int, timing: dict):
    """Store timing information for a data item (appended to a list)."""
    try:
        data = load_data()
        if data_idx >= len(data) or data_idx < 0:
            raise HTTPException(status_code=404, detail="Index out of range")
        timing_entry = {"duration": timing.get(
            "duration", 0), "change": timing.get("change", False)}
        if DATA_FILE_TYPE == "json":
            item = data[data_idx]
            if "timings" not in item or not isinstance(item["timings"], list):
                item["timings"] = []
            item["timings"].append(timing_entry)
            save_data(data)
        else:
            df = data
            timings_col = df.at[data_idx,
                                "timings"] if "timings" in df.columns else None
            try:
                timings = json.loads(timings_col) if timings_col else []
            except Exception:
                timings = []
            timings.append(timing_entry)
            df.at[data_idx, "timings"] = json.dumps(
                timings, ensure_ascii=False)
            save_data(df)
        return {"message": "Timing gespeichert"}
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"{DATA_FILE_PATH} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



def auto_add_missing_positions():
    """Automatically add missing position data for existing phrases."""
    if not AUTO_POSITIONS:
        print("ℹ️  Auto position filling disabled (use --auto-positions to enable)")
        return

    print("🔍 Scanning for missing position data...")

    try:
        data = load_data()
        data_changed = False
        updated_count = 0

        if DATA_FILE_TYPE == "json":
            # Handle JSON format
            for item in data:
                if 'text' not in item:
                    continue

                text = item['text']
                label_data = item.get('label', [])

                # Handle both string and array formats
                if isinstance(label_data, str):
                    if not label_data or label_data == '':
                        continue
                    try:
                        annotations = json.loads(label_data)
                    except (json.JSONDecodeError, TypeError):
                        continue
                else:
                    # Already an array
                    annotations = label_data

                if not isinstance(annotations, list):
                    continue

                annotations_updated = False

                for annotation in annotations:
                    # Check aspect_term positions
                    if ('aspect_term' in annotation and
                        annotation['aspect_term'] and
                        annotation['aspect_term'] != 'NULL' and
                            ('at_start' not in annotation or 'at_end' not in annotation)):

                        phrase = annotation['aspect_term']
                        start_pos = text.find(phrase)
                        if start_pos != -1:
                            annotation['at_start'] = start_pos
                            annotation['at_end'] = start_pos + len(phrase) - 1
                            annotations_updated = True
                            updated_count += 1

                    # Check opinion_term positions
                    if ('opinion_term' in annotation and
                        annotation['opinion_term'] and
                        annotation['opinion_term'] != 'NULL' and
                            ('ot_start' not in annotation or 'ot_end' not in annotation)):

                        phrase = annotation['opinion_term']
                        start_pos = text.find(phrase)
                        if start_pos != -1:
                            annotation['ot_start'] = start_pos
                            annotation['ot_end'] = start_pos + len(phrase) - 1
                            annotations_updated = True
                            updated_count += 1

                if annotations_updated:
                    # Store as array, not as JSON string
                    item['label'] = annotations
                    data_changed = True

        else:
            # Handle CSV format
            for idx, row in data.iterrows():
                if pd.isna(row.get('text')):
                    continue

                text = row['text']
                label_str = row.get('label', '')

                if not label_str or pd.isna(label_str) or label_str == '':
                    continue

                try:
                    annotations = json.loads(label_str)
                    if not isinstance(annotations, list):
                        continue

                    annotations_updated = False

                    for annotation in annotations:
                        # Check aspect_term positions
                        if ('aspect_term' in annotation and
                            annotation['aspect_term'] and
                            annotation['aspect_term'] != 'NULL' and
                                ('at_start' not in annotation or 'at_end' not in annotation)):

                            phrase = annotation['aspect_term']
                            start_pos = text.find(phrase)
                            if start_pos != -1:
                                annotation['at_start'] = start_pos
                                annotation['at_end'] = start_pos + \
                                    len(phrase) - 1
                                annotations_updated = True
                                updated_count += 1

                        # Check opinion_term positions
                        if ('opinion_term' in annotation and
                            annotation['opinion_term'] and
                            annotation['opinion_term'] != 'NULL' and
                                ('ot_start' not in annotation or 'ot_end' not in annotation)):

                            phrase = annotation['opinion_term']
                            start_pos = text.find(phrase)
                            if start_pos != -1:
                                annotation['ot_start'] = start_pos
                                annotation['ot_end'] = start_pos + \
                                    len(phrase) - 1
                                annotations_updated = True
                                updated_count += 1

                    if annotations_updated:
                        data.at[idx, 'label'] = json.dumps(
                            annotations, ensure_ascii=False)
                        data_changed = True

                except (json.JSONDecodeError, TypeError):
                    continue

        if data_changed:
            save_data(data)
            print(
                f"✅ Auto-added {updated_count} missing position entries and saved to {DATA_FILE_PATH}")
        else:
            print("ℹ️  No missing positions found")

    except Exception as e:
        print(f"❌ Error during auto position filling: {e}")

# POST Endpoint to manually trigger position data addition


@app.post("/auto-add-positions")
def manual_auto_add_positions():
    """HTTP-triggerable endpoint to auto-fill missing position data.

    Calls auto_add_missing_positions() which scans the dataset and adds
    at_start/at_end/ot_start/ot_end fields for any phrases missing them.
    Only fills positions when AUTO_POSITIONS is True.
    """
    try:
        auto_add_missing_positions()
        return {"message": "Position data auto-addition completed successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error adding position data: {str(e)}")


# ermittel die n Beispiele die am ähnlichsten zum input text sind



    return [examples[i] for i in top_indices]


@app.get("/ai_prediction/{data_idx}")
def get_ai_prediction(data_idx: int):
    """Generate AI predictions for a row using the configured LLM provider.

    Collects few-shot examples from other labeled rows, builds the prediction
    prompt via build_prediction_prompt(), dispatches to the provider selected
    via --llm-provider (or auto-derived), and adds position data if
    save_phrase_positions is enabled.

    Args:
        data_idx: 0-based row index.

    Returns:
        List of predicted aspect dicts with keys: aspect_term, aspect_category,
        sentiment_polarity, opinion_term, at_start, at_end, ot_start, ot_end.
    """
    try:
        data = load_data()
        config = load_config()
        default_aspects = config.get('aspect_categories', [])
        examples = []
        # Branch by file type
        if DATA_FILE_TYPE == "json":
            # JSON data is a list of dicts
            if data_idx < 0 or data_idx >= len(data):
                raise HTTPException(
                    status_code=404, detail="Index out of range")
            item = data[data_idx]
            text = item.get('text', '')
            # Collect examples with non-empty labels
            for entry in data:
                lbl = entry.get('label', [])
                if isinstance(lbl, list) and lbl:
                    examples.append(
                        {'text': entry.get('text', ''), 'label': lbl})
            aspect_categories = item.get(
                'aspect_category_list', default_aspects)
        else:
            # CSV data is a DataFrame
            df = data
            if data_idx < 0 or data_idx >= len(df):
                raise HTTPException(
                    status_code=404, detail="Index out of range")
            # Current row
            row = df.iloc[data_idx].to_dict()
            text = row.get('text', '')
            # Collect examples with non-empty label field
            for _, r in df.iterrows():
                lbl_str = r.get('label', '')
                if pd.isna(lbl_str) or lbl_str == '':
                    continue
                try:
                    lbl = json.loads(lbl_str)
                    if isinstance(lbl, list) and lbl:
                        examples.append(
                            {'text': r.get('text', ''), 'label': lbl})
                except Exception:
                    continue
            # Determine aspect categories per example
            raw_aspects = row.get('aspect_category_list', None)
            aspect_categories = raw_aspects if raw_aspects else default_aspects

        # filter examples that are identical to the requested text
        examples = [ex for ex in examples if ex['text'] != text]

        # Dispatch to the configured LLM provider via the port/adapter pattern
        try:
            provider_name = _derive_provider(CONFIG_DATA)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Validate provider configuration
        from services.llm_providers import validate_provider_config
        val_errors = validate_provider_config(provider_name, CONFIG_DATA)
        if val_errors:
            raise HTTPException(status_code=400, detail=val_errors[0])

        provider = get_provider(provider_name, CONFIG_DATA)
        prompt_template = CONFIG_DATA.get('labeling_prompt_template', DEFAULT_LABELING_TEMPLATE)
        predictions = provider.predict(
            text,
            config.get('sentiment_elements', [
                       "aspect_term", "aspect_category", "sentiment_polarity", "opinion_term"]),
            examples,
            aspect_categories,
            config.get('sentiment_polarity_options', [
                       "positive", "negative", "neutral"]),
            allow_implicit_aspect_terms=config.get(
                'implicit_aspect_term_allowed', True),
            allow_implicit_opinion_terms=config.get(
                'implicit_opinion_term_allowed', False),
            n_few_shot=config.get('n_few_shot', 10),
            llm_model=config.get('llm_model', 'gemma3:4b'),
            prompt_template=prompt_template
        )[0]
        predictions = predictions["aspects"]

        # if position saving is enabled, add positions to predictions
        if config.get('save_phrase_positions', True) and not config.get("disable-save-positions", False):
            for aspect in predictions:
                if 'aspect_term' in aspect and aspect['aspect_term'] != 'NULL':
                    start, end = find_phrase_positions(
                        text, aspect['aspect_term'])
                    aspect['at_start'] = start
                    aspect['at_end'] = end
                if 'opinion_term' in aspect and aspect['opinion_term'] != 'NULL':
                    start, end = find_phrase_positions(
                        text, aspect['opinion_term'])
                    aspect['ot_start'] = start
                    aspect['ot_end'] = end

        return predictions
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error loading prediction: {str(e)}")


@app.get("/live_prediction/{data_idx}")
def get_live_prediction(data_idx: int, role: str = "model_a"):
    """Generate AI predictions using per-model config (Live Compare Mode).

    Reads per-model config keys (role_provider, role_model, role_prompt,
    role_temperature) instead of global llm_provider. Each model (A, B)
    must have its own provider and model configured — no fallback.

    Args:
        data_idx: 0-based row index.
        role: 'model_a' or 'model_b'.

    Returns:
        List of predicted aspect dicts with keys: aspect_term, aspect_category,
        sentiment_polarity, opinion_term, at_start, at_end, ot_start, ot_end.
    """
    if role not in ("model_a", "model_b"):
        raise HTTPException(
            status_code=400, detail=f"Unknown role '{role}'. Use 'model_a' or 'model_b'.")

    try:
        data = load_data()
        config = load_config()
        default_aspects = config.get('aspect_categories', [])
        examples = []

        # Read per-model config keys from live in-memory config (CONFIG_DATA)
        # so that settings panel PATCH updates take effect immediately.
        provider_name = CONFIG_DATA.get(f"{role}_provider")
        llm_model = CONFIG_DATA.get(f"{role}_model")
        prompt_template = CONFIG_DATA.get(f"{role}_prompt")
        temperature = CONFIG_DATA.get(f"{role}_temperature", 0.7)

        # Validate per-model config is complete (no fallback)
        from services.llm_providers import validate_per_model_config
        val_errors = validate_per_model_config(role, CONFIG_DATA)
        if val_errors:
            raise HTTPException(status_code=400, detail="; ".join(val_errors))

        # Load the review text and collect examples
        if DATA_FILE_TYPE == "json":
            if data_idx < 0 or data_idx >= len(data):
                raise HTTPException(status_code=404, detail="Index out of range")
            item = data[data_idx]
            text = item.get('text', '')
            for entry in data:
                lbl = entry.get('label', [])
                if isinstance(lbl, list) and lbl:
                    examples.append({'text': entry.get('text', ''), 'label': lbl})
            aspect_categories = item.get('aspect_category_list', default_aspects)
        else:
            df = data
            if data_idx < 0 or data_idx >= len(df):
                raise HTTPException(status_code=404, detail="Index out of range")
            row = df.iloc[data_idx].to_dict()
            text = row.get('text', '')
            for _, r in df.iterrows():
                lbl_str = r.get('label', '')
                if pd.isna(lbl_str) or lbl_str == '':
                    continue
                try:
                    lbl = json.loads(lbl_str)
                    if isinstance(lbl, list) and lbl:
                        examples.append({'text': r.get('text', ''), 'label': lbl})
                except Exception:
                    continue
            raw_aspects = row.get('aspect_category_list', None)
            aspect_categories = raw_aspects if raw_aspects else default_aspects

        # Filter out examples identical to the requested text
        examples = [ex for ex in examples if ex['text'] != text]

        # Validate provider has required global keys (API keys, URLs)
        from services.llm_providers import validate_provider_config
        prov_errors = validate_provider_config(provider_name, CONFIG_DATA)
        if prov_errors:
            raise HTTPException(status_code=400, detail=prov_errors[0])

        # Dispatch to provider with per-model config
        from services.llm_providers import get_provider
        provider = get_provider(provider_name, CONFIG_DATA)
        predictions = provider.predict(
            text,
            CONFIG_DATA.get('sentiment_elements', [
                       "aspect_term", "aspect_category", "sentiment_polarity", "opinion_term"]),
            examples,
            aspect_categories,
            CONFIG_DATA.get('sentiment_polarity_options', [
                       "positive", "negative", "neutral"]),
            allow_implicit_aspect_terms=CONFIG_DATA.get('implicit_aspect_term_allowed', True),
            allow_implicit_opinion_terms=CONFIG_DATA.get('implicit_opinion_term_allowed', False),
            n_few_shot=CONFIG_DATA.get('n_few_shot', 10),
            llm_model=llm_model,
            prompt_template=prompt_template,
            temperature=temperature
        )[0]
        predictions = predictions["aspects"]

        # Add position data if saving is enabled
        if CONFIG_DATA.get('save_phrase_positions', True):
            for aspect in predictions:
                if 'aspect_term' in aspect and aspect['aspect_term'] != 'NULL':
                    start, end = find_phrase_positions(text, aspect['aspect_term'])
                    aspect['at_start'] = start
                    aspect['at_end'] = end
                if 'opinion_term' in aspect and aspect['opinion_term'] != 'NULL':
                    start, end = find_phrase_positions(text, aspect['opinion_term'])
                    aspect['ot_start'] = start
                    aspect['ot_end'] = end

        return predictions
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error in live prediction: {str(e)}")


@app.get("/avg-annotation-time")
def get_avg_annotation_time():
    """Calculate and return the average annotation time across all examples with timing data."""
    try:
        data = load_data()
        total_duration = 0.0
        total_entries = 0

        for idx, item in enumerate(data):
            if DATA_FILE_TYPE == "json":
                timings = item.get("timings", []) if isinstance(
                    item.get("timings"), list) else []
            else:
                # CSV: timings stored as JSON string in 'timings' column
                timings_str = item.get("timings") if hasattr(item, 'get') and callable(item.get) else (
                    data.iloc[idx]["timings"] if "timings" in data.columns and idx < len(
                        data) else None
                )
                try:
                    timings = json.loads(
                        timings_str) if timings_str and timings_str != '' else []
                except Exception:
                    timings = []

            # Sum all duration values for this example
            for timing_entry in timings:
                if isinstance(timing_entry, dict) and "duration" in timing_entry:
                    total_duration += timing_entry["duration"]
                    total_entries += 1

        avg_time = total_duration / total_entries if total_entries > 0 else 0.0

        return {
            "avg_annotation_time": round(avg_time, 2),
            "total_entries": total_entries,
            "total_duration": round(total_duration, 2)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error calculating average annotation time: {str(e)}")


import tempfile
import shutil

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/upload-data")
async def upload_data(file: UploadFile = File(...)):
    """Upload a CSV or JSON data file to use for annotation."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ('.csv', '.json'):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Upload .csv or .json files only."
        )

    # Save to uploads directory with a safe name
    safe_name = f"uploaded_{int(time.time())}{ext}"
    dest = os.path.join(UPLOAD_DIR, safe_name)

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Activate the uploaded file
    set_data_file(dest)

    # Load and return count
    try:
        data = load_data()
        count = len(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading uploaded file: {e}")

    print(f"📤 Uploaded data file: {dest} ({count} rows)")
    return {"message": f"Loaded {file.filename} ({count} satır)", "total_count": count, "file_path": dest}


@app.on_event("startup")
async def startup_event():
    """Run startup tasks including auto-adding missing position data."""
    print(f"🚀 Starting AnnoABSA Backend...")
    print(f"📄 Data file: {DATA_FILE_PATH} (type: {DATA_FILE_TYPE})")
    if CONFIG_PATH:
        print(f"⚙️  Config file: {CONFIG_PATH}")

    # Auto-add missing position data when server starts (only if enabled)
    if AUTO_POSITIONS:
        print("🔧 Auto-positions feature enabled - scanning for missing position data...")
        auto_add_missing_positions()
    else:
        print("ℹ️  Auto-positions feature disabled (use --auto-positions to enable)")

    print("✨ Backend ready!")

# BM25-based similarity matching (no caching needed)





@app.post("/review/{data_idx}/save")
def save_review_triplets(data_idx: int, req: SaveTripletsRequest):
    """Save annotation triplets for a given row (the PRIMARY save endpoint).

    The frontend's handleNextReview calls this (not POST /annotations/{data_idx}).
    Accepts a list of triplet dicts and stores them in the label field.

    Args:
        data_idx: 0-based row index.
        req: SaveTripletsRequest with {triplets: list} of annotation dicts.

    Returns:
        dict: {status, message, next_index}
    """
    try:
        data = load_data()
        if data_idx >= len(data) or data_idx < 0:
            raise HTTPException(status_code=404, detail="Index out of range")
        
        triplets_list = req.triplets
        if DATA_FILE_TYPE == "json":
            data[data_idx]["label"] = triplets_list
            save_data(data)
        else:
            df = data
            triplets_json = json.dumps(triplets_list, ensure_ascii=False)
            df.at[data_idx, "label"] = triplets_json
            save_data(df)

        # If a new review_text was provided, update the data file
        if req.review_text is not None:
            if DATA_FILE_TYPE == "json":
                # JSON: prefer review_text key, fall back to text
                if "review_text" in data[data_idx]:
                    data[data_idx]["review_text"] = req.review_text
                else:
                    data[data_idx]["text"] = req.review_text
                save_data(data)
            else:
                # CSV: prefer review_text column, fall back to text
                if "review_text" in df.columns:
                    df.at[data_idx, "review_text"] = req.review_text
                else:
                    df.at[data_idx, "text"] = req.review_text
                save_data(df)

        return {"status": "success", "message": "İnceleme tripletleri başarıyla kaydedildi.", "next_index": data_idx + 1}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/chat")
def agent_chat(req: AgentChatRequest):
    """Handle chat messages from the Helper Agent panel (POST /agent/chat).

    Builds a system prompt with the review text and model comparison data,
    appends the last 4 turns of conversation history, dispatches to the
    configured LLM provider. Falls back to hardcoded Turkish rule-based
    responses when the provider is unavailable.

    Args:
        req: AgentChatRequest with review_text, model_a/b_triplets,
             user_message, chat_history.

    Returns:
        dict: {reply: str}
    """
    config = load_config()
    model_a_name = config.get("compare_model_a_name", "Model A")
    model_b_name = config.get("compare_model_b_name", "Model B")

    # Read per-agent config (falls back to global if per-agent provider is unset)
    agent_provider = CONFIG_DATA.get("helper_agent_provider") or None
    agent_model = CONFIG_DATA.get("helper_agent_model") or None
    agent_temperature = CONFIG_DATA.get("helper_agent_temperature", 0.7)

    # Build chat messages using per-agent prompt (or default template)
    chat_template = CONFIG_DATA.get("helper_agent_prompt") or CONFIG_DATA.get('helper_agent_prompt_template', DEFAULT_CHAT_TEMPLATE)
    system_content = chat_template.format(
        review_text=req.review_text,
        model_a_name=model_a_name,
        model_a_triplets=req.model_a_triplets,
        model_b_name=model_b_name,
        model_b_triplets=req.model_b_triplets,
    )
    messages = [
        {"role": "system", "content": system_content}
    ]
    for h in req.chat_history[-4:]:
        role = "assistant" if h.get("sender") == "agent" else "user"
        messages.append({"role": role, "content": h.get("text", "")})
    messages.append({"role": "user", "content": req.user_message})

    # Dispatch to configured provider
    try:
        # Use per-agent provider if set, otherwise fall back to derived global
        if agent_provider:
            provider_name = agent_provider
        else:
            provider_name = _derive_provider(CONFIG_DATA)
        from services.llm_providers import validate_provider_config
        val_errors = validate_provider_config(provider_name, config)
        if val_errors:
            raise ValueError(val_errors[0])

        provider = get_provider(provider_name, CONFIG_DATA)
        reply = provider.chat(
            messages=messages,
            model=agent_model or config.get("llm_model", "gemma3:4b"),
            temperature=agent_temperature,
            max_tokens=300
        )
        return {"reply": reply}
    except Exception as e:
        print(f"Provider chat error: {e}")

    # Fallback: hardcoded Turkish rule-based responses (backward compat when no provider configured)
    msg = req.user_message.lower()
    reply = "Helper agent: "
    if "model a" in msg or model_a_name.lower() in msg:
        reply += f"{model_a_name} modeli cümlenin yan cümleciklerini ('manzara şahane' ve 'servis rezalet') ayrı ayrı değerlendirmiş. Zıtlık bağlaçlarını iyi çözdüğü için {model_a_name} tripletleri daha tutarlı."
    elif "model b" in msg or model_b_name.lower() in msg:
        reply += f"{model_b_name} modeli ana duyguya odaklandığı için bazen olumsuz yan etiketleri kaçırabiliyor. {model_b_name} çıktısında doğru olanları seçip eksikleri orta formdan ekleyebilirsin."
    elif "neden" in msg or "niye" in msg or "hangisi" in msg:
        reply += "Metinde zıtlık bağlacı olduğu için iki model farklı sonuç üretmiş. Benim önerim hem yeşil (positive) hem kırmızı (negative) etiketleri seçerek tam kapsamlı etiketleme yapman."
    else:
        reply += f"\"{req.user_message}\" mesajını aldım. Hem {model_a_name} hem {model_b_name} çıktısındaki doğru tripletleri işaretleyip sağ alttaki \"press for next review\" butonuna basarak kaydedebilirsin."

    return {"reply": reply}
