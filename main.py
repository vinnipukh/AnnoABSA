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

# ── Prompt template defaults (Turkish, configurable) ──────────────

DEFAULT_LABELING_TEMPLATE = (
    "Aşağıdaki duygu unsuru tanımlarına göre:\n"
    "\n"
    "- 'aspect term' (görünüş terimi), kullanıcının bir ürün veya hizmetin belirli bir özelliği "
    "hakkında görüş belirttiği, metindeki tam kelime veya kelime öbeğidir. {implicit_aspect_note}\n"
    "- 'aspect category' (görünüş kategorisi), görünüşün ait olduğu kategoridir. Mevcut kategoriler "
    "(bu kategori adlarını İngilizce olduğu gibi bırakın, çevirmeyin): {aspect_categories}\n"
    "- 'sentiment polarity' (duygu kutbu), ifade edilen görüşün olumluluk, olumsuzluk ya da nötrlük "
    "derecesidir. Mevcut kutuplar (İngilizce olduğu gibi bırakın, çevirmeyin): {polarities}\n"
    "- 'opinion term' (görüş terimi), kullanıcının bir görünüşe yönelik tutumunu ifade eden, "
    "metindeki tam kelime veya kelime öbeğidir. {implicit_opinion_note}\n"
    "\n"
    "Metin Türkçedir ve Türkçe sondan eklemeli (agglutinative) bir dildir: aynı kök farklı çekim "
    "ekleriyle görünebilir (ör. \"kitap\", \"kitabı\", \"kitaplarımdan\"). Görünüş ve görüş "
    "terimlerini ararken kelimenin metindeki tam, çekimli halini seçin — kökü ayırıp yeniden "
    "yazmayın.\n"
    "\n"
    "Aşağıdaki metindeki tüm duygu unsurlarını, karşılık gelen {element_names} ile birlikte, her "
    "biri {element_keys} anahtarlarına sahip nesnelerden oluşan bir liste biçiminde tanıyın."
)

DEFAULT_CHAT_TEMPLATE = (
    'Sen ABSA (Aspect-Based Sentiment Analysis) veri etiketleme asistanısın. '
    'Şu incelemeyi tartışıyorsunuz: "{review_text}". '
    '{model_a_name} tripletleri: {model_a_triplets}, '
    '{model_b_name} tripletleri: {model_b_triplets}. '
    "Kullanıcıya mantıklı, akıl yürüterek açıklama yap."
)

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
    """Set the data file path and determine file type."""
    global DATA_FILE_PATH, DATA_FILE_TYPE
    DATA_FILE_PATH = file_path
    DATA_FILE_TYPE = "json" if file_path.endswith('.json') else "csv"


def set_config_file(config_path: str):
    """Set the config file path."""
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
        "store_time": False,
        "display_avg_annotation_time": False,
        "enable_pre_prediction": False,
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
        "helper_agent_prompt_template": DEFAULT_CHAT_TEMPLATE
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


# Datenmodell für POST Requests
class Item(BaseModel):
    name: str
    value: int

# Datenmodell für Annotations


class AnnotationData(BaseModel):
    name: str
    value: list

class SaveTripletsRequest(BaseModel):
    triplets: list

class AgentChatRequest(BaseModel):
    review_text: str
    model_a_triplets: list = []
    model_b_triplets: list = []
    user_message: str
    chat_history: list = []


# GET Endpoint


@app.get("/settings")
def get_settings():
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
        "store_time": CONFIG_DATA.get("store_time", False),
        "display_avg_annotation_time": CONFIG_DATA.get("display_avg_annotation_time", False),
        "enable_pre_prediction": CONFIG_DATA.get("enable_pre_prediction", CONFIG_DATA.get("enable_preprediction", False)),
        "disable_ai_automatic_prediction": CONFIG_DATA.get("disable_ai_automatic_prediction", False),
        "annotation_guideline": CONFIG_DATA.get("annotation_guideline", None),
        "current_index": get_current_index(),
        "max_number_of_idxs": max_number_of_idxs()
    }

    # Add session_id if it exists
    if CONFIG_DATA.get("session_id"):
        settings["session_id"] = CONFIG_DATA["session_id"]

    return settings




import ast

def parse_triplet_column(raw_val, prefix="t"):
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

def generate_mock_reasoning(text: str, model_a_name: str, model_b_name: str, model_a_list: list, model_b_list: list) -> str:
    if not text:
        return "Helper agent: İnceleme seçilmedi."
    model_a_aspects = [t.get("aspect_term", "") for t in model_a_list if t.get("aspect_term")]
    model_b_aspects = [t.get("aspect_term", "") for t in model_b_list if t.get("aspect_term")]

    common = set(model_a_aspects).intersection(set(model_b_aspects))
    only_a = set(model_a_aspects) - set(model_b_aspects)
    only_b = set(model_b_aspects) - set(model_a_aspects)

    reasoning = f"Helper agent: Merhaba! İncelemeyi analiz ettim: **\"{text}\"**.\n\n"
    if common:
        reasoning += f"• **Ortak Tespitler:** Her iki model de `{', '.join(common)}` ögelerini doğru yakalamış.\n"
    if only_a:
        reasoning += f"• **{model_a_name} Farkı:** {model_a_name} ek olarak `{', '.join(only_a)}` ögesini tespit etmiş. Bağlama göre bu mantıklı.\n"
    if only_b:
        reasoning += f"• **{model_b_name} Farkı:** {model_b_name} ise `{', '.join(only_b)}` ögesini öne çıkarmış.\n"

    if model_a_list and model_b_list:
        if len(model_a_list) >= len(model_b_list):
            reasoning += f"\n💡 **Önerim:** {model_a_name} duygu polaritelerini daha detaylı ayrıştırmış görünüyor. {model_a_name} çıktısını temel alıp eksikleri manuel tamamlayabilirsin."
        else:
            reasoning += f"\n💡 **Önerim:** {model_b_name} özetlemeyi daha net yapmış. {model_b_name} tripletlerini onaylamanı tavsiye ederim."
    elif model_a_list:
        reasoning += f"\n💡 **Önerim:** {model_b_name} bu satırda çıktı üretmemiş. {model_a_name} tripletlerini kontrol edip onaylayabilirsin."
    elif model_b_list:
        reasoning += f"\n💡 **Önerim:** {model_a_name} bu satırda çıktı üretmemiş. {model_b_name} tripletlerini seçebilirsin."
    else:
        reasoning += "\n💡 **Önerim:** Modeller bu incelemede herhangi bir triplet çıkaramamış. Orta kolondaki formdan manuel giriş yapmalısın."

    return reasoning
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
    try:
        data = load_data()
        return len(data)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"{DATA_FILE_PATH} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_current_index():
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
    try:
        data = load_data()
        return len(data)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"{DATA_FILE_PATH} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# POST Endpoint


@app.post("/data/{data_idx}")
def post_data(data_idx: int, item: Item):
    # add value to row label
    try:
        df = pd.read_csv("annotations.csv")
        if data_idx >= len(df) or data_idx < 0:
            raise HTTPException(status_code=404, detail="Index out of range")
        df.at[data_idx, 'label'] = item.value
        df.to_csv("annotations.csv", index=False)
        return {"message": "Data updated successfully"}
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail="annotations.csv not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# POST Endpoint for Annotations


@app.post("/annotations/{data_idx}")
def post_annotations(data_idx: int, annotation_data: AnnotationData):
    try:
        data = load_data()
        if data_idx >= len(data) or data_idx < 0:
            raise HTTPException(status_code=404, detail="Index out of range")

        annotation_data = annotation_data.value

        if DATA_FILE_TYPE == "json":
            # Update JSON format - set "label" key with annotation data
            data[data_idx]['label'] = annotation_data
            save_data(data)
        else:
            # Update CSV format
            df = data
            annotations_json = json.dumps(annotation_data)
            df.at[data_idx, 'label'] = annotations_json
            save_data(df)

        return {"message": "Annotations saved successfully"}
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"{DATA_FILE_PATH} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Timing-Logik: Speichere pro Beispiel eine Liste von {duration, change}


@app.post("/timing/{data_idx}")
def post_timing(data_idx: int, timing: dict):
    """Speichere Timing-Informationen für ein Beispiel (append an Liste)."""
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


def find_phrase_positions(text: str, phrase: str):
    """
    Find start and end positions of a phrase in text.
    Returns tuple (start, end) or (None, None) if not found.
    """
    if not phrase or phrase == "NULL" or not text:
        return None, None

    # Try exact match first
    index = text.find(phrase)
    if index != -1:
        return index, index + len(phrase) - 1

    # If exact match fails, try case-insensitive match
    index = text.lower().find(phrase.lower())
    if index != -1:
        return index, index + len(phrase) - 1

    return None, None


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
    """Manually trigger the auto-addition of missing position data."""
    try:
        auto_add_missing_positions()
        return {"message": "Position data auto-addition completed successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error adding position data: {str(e)}")


def predict_llm(text, considered_sentiment_elements, examples, aspect_categories, polarities, allow_implicit_aspect_terms=False, allow_implicit_opinion_terms=False, n_few_shot=10, llm_model="gemma3:4b", prompt_template=None):
    """Predict sentiment elements using Ollama (backward-compatible wrapper)."""
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
        return [], few_shot_examples
    else:
        return json.loads(response.response), few_shot_examples


def predict_openai(text, considered_sentiment_elements, examples, aspect_categories, polarities, allow_implicit_aspect_terms=False, allow_implicit_opinion_terms=False, n_few_shot=10, llm_model="gpt-4o-2024-08-06", openai_key=None, prompt_template=None):
    """Predict sentiment elements using OpenAI (backward-compatible wrapper)."""
    from openai import OpenAI
    import json

    if not openai_key:
        raise ValueError("OpenAI API key is required for OpenAI predictions")

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
        print("🔍 Sending request to OpenAI...")
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
            # Convert to same format as Ollama response
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


# ermittel die n Beispiele die am ähnlichsten zum input text sind


def get_most_similar_examples(input_text, examples, n):
    """Return up to n most similar example annotations based on input_text using BM25"""

    # If no examples available, return empty list
    if not examples:
        return []

    # Limit n to available examples
    n = min(n, len(examples))

    # Early exit if only need 1 example and we have examples
    if n == 1 and len(examples) == 1:
        return examples

    # Convert input_text to string if it's a tuple
    if isinstance(input_text, tuple):
        input_text_str = input_text[0]  # Assume first element is the text
    else:
        input_text_str = str(input_text)

    # Extract text from examples
    example_texts = []
    for ex in examples:
        if isinstance(ex, dict) and 'text' in ex:
            text = str(ex['text'])
        elif isinstance(ex, tuple):
            text = str(ex[0])  # Assume first element is the text
        else:
            text = str(ex)
        example_texts.append(text)

    # Tokenize texts for BM25
    def tokenize(text):
        # Simple tokenization: lowercase and split on whitespace/punctuation
        return re.findall(r'\b\w+\b', text.lower())

    tokenized_examples = [tokenize(text) for text in example_texts]
    tokenized_query = tokenize(input_text_str)

    # Create BM25 model and get scores
    if BM25Okapi is None:
        return examples[:n]
        
    bm25 = BM25Okapi(tokenized_examples)
    scores = bm25.get_scores(tokenized_query)

    # Get top n indices
    if n < len(examples):
        # Get indices of top n scores
        top_indices = np.argsort(scores)[-n:][::-1]  # Sort descending
    else:
        # If we need all examples, just sort everything
        top_indices = np.argsort(scores)[::-1]

    return [examples[i] for i in top_indices]


def find_valid_phrases_list(text, max_tokens_in_phrase=None):
    phrases = []
    # identify split positions based on punctuation and spaces
    split_positions = [0]
    for match in re.finditer(r'(?<=\w)(?=[,\.\!\?\;\:])|[\s]+', text):
        split_positions.append(match.end())

    n_splits = len(split_positions)
    if max_tokens_in_phrase is None:
        max_tokens_in_phrase = n_splits

    # print all phrases between split positions
    for i in range(len(split_positions)):
        for j in range(i+1, len(split_positions)):
            phrase = text[split_positions[i]:split_positions[j]].strip()
            if phrase:
                num_tokens = len(phrase.split())
                if num_tokens <= max_tokens_in_phrase:
                    phrases.append(phrase)

    # remove phrases with special characters at the beginning or end
    phrases = [p for p in phrases if re.match(r'^[\w].*[\w]$', p)]

    return phrases


def build_prediction_prompt(text, considered_sentiment_elements, examples, aspect_categories, polarities, allow_implicit_aspect_terms, allow_implicit_opinion_terms, n_few_shot, prompt_template=None):
    """Build the ABSA prediction prompt and retrieve few-shot examples.

    Shared by all LLM provider adapters. Returns (prompt_str, few_shot_examples).

    When prompt_template is provided (str), uses it with .format() substitution
    — placeholders: {implicit_aspect_note}, {implicit_opinion_note},
    {aspect_categories}, {polarities}, {element_names}, {element_keys}.
    When prompt_template is None, falls back to the original hardcoded English prompt.
    """
    few_shot_examples = get_most_similar_examples(text, examples, n=n_few_shot)

    if prompt_template is not None:
        # ── Template-based (configurable) prompt ──────────────────────
        implicit_aspect_note = (
            "Görünüş terimi örtük (implicit) ise 'NULL' olabilir."
            if allow_implicit_aspect_terms else ""
        )
        implicit_opinion_note = (
            "Görüş terimi örtük (implicit) ise 'NULL' olabilir."
            if allow_implicit_opinion_terms else ""
        )
        aspect_categories_str = ", ".join(aspect_categories)
        polarities_str = ", ".join(polarities)
        element_names_str = ", ".join(
            e.replace("_", " ") + "s" for e in considered_sentiment_elements
        )
        element_keys_str = ", ".join(
            f"'{e.replace('_', ' ')}'" for e in considered_sentiment_elements
        )

        prompt_head = prompt_template.format(
            implicit_aspect_note=implicit_aspect_note,
            implicit_opinion_note=implicit_opinion_note,
            aspect_categories=aspect_categories_str,
            polarities=polarities_str,
            element_names=element_names_str,
            element_keys=element_keys_str,
        )
    else:
        # ── Original hardcoded English prompt (backward compat) ──────
        prompt_head = "According to the following sentiment elements definition: \n\n"

        if "aspect_term" in considered_sentiment_elements:
            prompt_head += "- The 'aspect term' is the exact word or phrase in the text that represents a specific feature, attribute, or aspect of a product or service that a user may express an opinion about. "
            if allow_implicit_aspect_terms:
                prompt_head += "The aspect term might be 'NULL' for implicit aspect."
            prompt_head += "\n"
        if "aspect_category" in considered_sentiment_elements:
            prompt_head += f"- The 'aspect category' refers to the category that aspect belongs to, and the available categories includes: {', '.join(aspect_categories)}.\n"
        if "sentiment_polarity" in considered_sentiment_elements:
            prompt_head += f"- The 'sentiment polarity' refers to the degree of positivity, negativity or neutrality expressed in the opinion towards a particular aspect or feature of a product or service, and the available polarities include: {', '.join(polarities)}.\n"
        if "opinion_term" in considered_sentiment_elements:
            prompt_head += "- The 'opinion term' is the exact word or phrase in the text that refers to the sentiment or attitude expressed by a user towards a particular aspect or feature of a product or service. "
            if allow_implicit_opinion_terms:
                prompt_head += "The opinion term might be 'NULL' for implicit opinion."
            prompt_head += "\n"

        prompt_head += "\nRecognize all sentiment elements with their corresponding "
        for element in considered_sentiment_elements:
            prompt_head += element.replace("_", " ") + "s, "
        prompt_head = prompt_head[:-2]
        prompt_head += " in the following text in the form of a list of objects, each object having key(s) "
        for element in considered_sentiment_elements:
            prompt_head += f"'{element.replace('_', ' ')}', "
        prompt_head = prompt_head[:-2]
        prompt_head += ".\n\n"

    # ── Common suffix: few-shot examples + target text ──────────────
    if few_shot_examples:
        prompt = prompt_head + "Here are some examples:\n"
        for ex in few_shot_examples:
            prompt += f"Text: {ex['text']}\n"
            prompt += "Sentiment elements: ["
            for label in ex['label']:
                prompt += "("
                for element in considered_sentiment_elements:
                    prompt += f"'{element.replace('_', ' ')}': '{label[element]}', "
                prompt = prompt[:-2]
                prompt += "), "
            prompt = prompt[:-2]
            prompt += "]\n"
    else:
        prompt = prompt_head
    prompt += f"Text: {text}\nSentiment elements: "

    return prompt, few_shot_examples


def build_absa_models(text, considered_sentiment_elements, polarities, aspect_categories, allow_implicit_aspect_terms, allow_implicit_opinion_terms):
    """Build dynamic Pydantic model and Enums for structured ABSA output.

    Returns (Aspects_model, field_types_dict, enums_dict).
    Shared by all LLM provider adapters that use structured JSON output.
    """
    from pydantic import BaseModel, create_model
    from enum import Enum

    allowed_phrases = find_valid_phrases_list(text)
    allowed_aspect_terms = allowed_phrases + \
        ["NULL"] if allow_implicit_aspect_terms else allowed_phrases
    allowed_opinion_terms = allowed_phrases + \
        ["NULL"] if allow_implicit_opinion_terms else allowed_phrases

    AspectEnum = Enum("AspectEnum", {p: p for p in allowed_aspect_terms})
    OpinionEnum = Enum("OpinionEnum", {p: p for p in allowed_opinion_terms})
    PolarityEnum = Enum("PolarityEnum", {p: p for p in polarities})
    CategoryEnum = Enum("CategoryEnum", {c: c for c in aspect_categories})

    field_types = {
        "aspect_term": (AspectEnum, ...),
        "aspect_category": (CategoryEnum, ...),
        "opinion_term": (OpinionEnum, ...),
        "sentiment_polarity": (PolarityEnum, ...)
    }

    SentimentElement = create_model(
        "SentimentElement",
        **{name: field_types[name] for name in considered_sentiment_elements}
    )

    class Aspects(BaseModel):
        aspects: list[SentimentElement]

    return Aspects, field_types, {"AspectEnum": AspectEnum, "OpinionEnum": OpinionEnum, "PolarityEnum": PolarityEnum, "CategoryEnum": CategoryEnum}


class OllamaProvider:
    """LLM provider adapter for Ollama (local)."""

    def __init__(self, config: dict):
        self.config = config

    def predict(self, text, considered_sentiment_elements, examples, aspect_categories, polarities, allow_implicit_aspect_terms, allow_implicit_opinion_terms, n_few_shot, llm_model, prompt_template=None):
        """Predict ABSA triplets via Ollama."""
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
        """Send a chat message via Ollama."""
        from ollama import chat as ollama_chat
        response = ollama_chat(
            model=model,
            messages=messages,
            options={"temperature": temperature, "max_tokens": max_tokens}
        )
        return response["message"]["content"]


class OpenAIProvider:
    """LLM provider adapter for OpenAI-compatible APIs."""

    def __init__(self, config: dict):
        self.config = config

    def predict(self, text, considered_sentiment_elements, examples, aspect_categories, polarities, allow_implicit_aspect_terms, allow_implicit_opinion_terms, n_few_shot, llm_model, prompt_template=None):
        """Predict ABSA triplets via OpenAI structured output."""
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
        """Send a chat message via OpenAI."""
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
    """LLM provider adapter for Anthropic."""

    def __init__(self, config: dict):
        self.config = config

    def predict(self, text, considered_sentiment_elements, examples, aspect_categories, polarities, allow_implicit_aspect_terms, allow_implicit_opinion_terms, n_few_shot, llm_model, prompt_template=None):
        """Predict ABSA triplets via Anthropic."""
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
        """Send a chat message via Anthropic."""
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
    """LLM provider adapter for vLLM (OpenAI-compatible)."""

    def __init__(self, config: dict):
        self.config = config

    def predict(self, text, considered_sentiment_elements, examples, aspect_categories, polarities, allow_implicit_aspect_terms, allow_implicit_opinion_terms, n_few_shot, llm_model, prompt_template=None):
        """Predict ABSA triplets via vLLM (OpenAI-compatible API)."""
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
        """Send a chat message via vLLM (OpenAI-compatible API)."""
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

    NOTE: cli.py has an inline copy of this logic that MUST be kept in sync
    (cannot import from main.py without triggering import-time side effects,
    same as the template constants in Task 4).
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


@app.get("/ai_prediction/{data_idx}")
def get_ai_prediction(data_idx: int):
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
        if provider_name == 'openai' and not config.get('openai_key'):
            raise HTTPException(
                status_code=400,
                detail="OpenAI provider selected but no API key configured. Use --openai-key."
            )
        if provider_name == 'anthropic' and not config.get('anthropic_key'):
            raise HTTPException(
                status_code=400,
                detail="Anthropic provider selected but no API key configured. Use --anthropic-key."
            )
        if provider_name == 'vllm' and not config.get('vllm_url'):
            raise HTTPException(
                status_code=400,
                detail="vLLM provider selected but no URL configured. Use --vllm-url."
            )

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

# Removed _load_embedding_cache function - BM25 doesn't need caching

# Removed _save_embedding_cache function - BM25 doesn't need caching

# Removed _get_sentence_model function - BM25 doesn't need sentence transformers

# Removed _get_cached_embedding function - BM25 doesn't need caching

# Removed _cleanup_embedding_cache function - BM25 doesn't need caching





@app.post("/review/{data_idx}/save")
def save_review_triplets(data_idx: int, req: SaveTripletsRequest):
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
            
        return {"status": "success", "message": "İnceleme tripletleri başarıyla kaydedildi.", "next_index": data_idx + 1}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/chat")
def agent_chat(req: AgentChatRequest):
    config = load_config()
    model_a_name = config.get("compare_model_a_name", "Model A")
    model_b_name = config.get("compare_model_b_name", "Model B")

    # Determine provider (same derivation as get_ai_prediction, via shared helper)
    provider_name = None

    # Build chat messages
    chat_template = CONFIG_DATA.get('helper_agent_prompt_template', DEFAULT_CHAT_TEMPLATE)
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
        provider_name = _derive_provider(CONFIG_DATA)
        if provider_name == 'openai' and not config.get('openai_key'):
            raise ValueError("OpenAI provider selected but no API key configured. Use --openai-key.")
        if provider_name == 'anthropic' and not config.get('anthropic_key'):
            raise ValueError("Anthropic provider selected but no API key configured. Use --anthropic-key.")
        if provider_name == 'vllm' and not config.get('vllm_url'):
            raise ValueError("vLLM provider selected but no URL configured. Use --vllm-url.")

        provider = get_provider(provider_name, CONFIG_DATA)
        reply = provider.chat(
            messages=messages,
            model=config.get("llm_model", "gemma3:4b"),
            temperature=0.7,
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
