"""AI prediction endpoints — GET /ai_prediction/{idx}, GET /live_prediction/{idx}."""
from fastapi import APIRouter, HTTPException
import main
from services import llm_providers
from services.prediction import DEFAULT_LABELING_TEMPLATE, find_phrase_positions
import json
import pandas as pd

router = APIRouter(tags=["ai"])


@router.get("/ai_prediction/{data_idx}")
def get_ai_prediction(data_idx: int):
    """Generate AI predictions for a row using the configured LLM provider."""
    try:
        data = main.load_data()
        config = main.load_config()
        default_aspects = config.get('aspect_categories', [])
        examples = []

        if main.DATA_FILE_TYPE == "json":
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

        examples = [ex for ex in examples if ex['text'] != text]

        try:
            provider_name = llm_providers._derive_provider(main.CONFIG_DATA)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        val_errors = llm_providers.validate_provider_config(provider_name, main.CONFIG_DATA)
        if val_errors:
            raise HTTPException(status_code=400, detail=val_errors[0])

        provider = llm_providers.get_provider(provider_name, main.CONFIG_DATA)
        prompt_template = main.CONFIG_DATA.get('labeling_prompt_template', DEFAULT_LABELING_TEMPLATE)
        predictions = provider.predict(
            text,
            config.get('sentiment_elements', ["aspect_term", "aspect_category", "sentiment_polarity", "opinion_term"]),
            examples,
            aspect_categories,
            config.get('sentiment_polarity_options', ["positive", "negative", "neutral"]),
            allow_implicit_aspect_terms=config.get('implicit_aspect_term_allowed', True),
            allow_implicit_opinion_terms=config.get('implicit_opinion_term_allowed', False),
            n_few_shot=config.get('n_few_shot', 10),
            llm_model=config.get('llm_model', 'gemma3:4b'),
            prompt_template=prompt_template
        )[0]
        predictions = predictions["aspects"]

        if config.get('save_phrase_positions', True) and not config.get("disable-save-positions", False):
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading prediction: {str(e)}")


@router.get("/live_prediction/{data_idx}")
def get_live_prediction(data_idx: int, role: str = "model_a"):
    """Generate AI predictions using per-model config (Live Compare Mode)."""
    if role not in ("model_a", "model_b"):
        raise HTTPException(status_code=400, detail=f"Unknown role '{role}'. Use 'model_a' or 'model_b'.")

    try:
        data = main.load_data()
        config = main.load_config()
        default_aspects = config.get('aspect_categories', [])
        examples = []

        provider_name = main.CONFIG_DATA.get(f"{role}_provider")
        llm_model = main.CONFIG_DATA.get(f"{role}_model")
        prompt_template = main.CONFIG_DATA.get(f"{role}_prompt")
        temperature = main.CONFIG_DATA.get(f"{role}_temperature", 0.7)

        val_errors = llm_providers.validate_per_model_config(role, main.CONFIG_DATA)
        if val_errors:
            raise HTTPException(status_code=400, detail="; ".join(val_errors))

        if main.DATA_FILE_TYPE == "json":
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

        examples = [ex for ex in examples if ex['text'] != text]

        prov_errors = llm_providers.validate_provider_config(provider_name, main.CONFIG_DATA)
        if prov_errors:
            raise HTTPException(status_code=400, detail=prov_errors[0])

        provider = llm_providers.get_provider(provider_name, main.CONFIG_DATA)
        predictions = provider.predict(
            text,
            main.CONFIG_DATA.get('sentiment_elements', ["aspect_term", "aspect_category", "sentiment_polarity", "opinion_term"]),
            examples,
            aspect_categories,
            main.CONFIG_DATA.get('sentiment_polarity_options', ["positive", "negative", "neutral"]),
            allow_implicit_aspect_terms=main.CONFIG_DATA.get('implicit_aspect_term_allowed', True),
            allow_implicit_opinion_terms=main.CONFIG_DATA.get('implicit_opinion_term_allowed', False),
            n_few_shot=main.CONFIG_DATA.get('n_few_shot', 10),
            llm_model=llm_model,
            prompt_template=prompt_template,
            temperature=temperature
        )[0]
        predictions = predictions["aspects"]

        if main.CONFIG_DATA.get('save_phrase_positions', True):
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
        raise HTTPException(status_code=500, detail=f"Error in live prediction: {str(e)}")
