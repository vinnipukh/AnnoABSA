"""Review data endpoints — GET /data/{idx}, POST /review/{idx}/save, POST /agent/chat."""
from fastapi import APIRouter, HTTPException
from app.config import CONFIG_DATA, DATA_FILE_PATH, DATA_FILE_TYPE
from app.data import load_data, save_data, parse_triplet_column, _load_comparison_csv, _load_4way_row
from models.schemas import SaveTripletsRequest, AgentChatRequest
from services import llm_providers
import json
import pandas as pd

router = APIRouter(tags=["reviews"])


@router.get("/data/{data_idx}")
def get_data(data_idx: int):
    """Return a single row's review text, label, and model comparison data."""
    from services.prediction import generate_mock_reasoning
    try:
        data = load_data()
        if data_idx >= len(data) or data_idx < 0:
            raise HTTPException(status_code=404, detail="Index out of range")

        default_aspects = CONFIG_DATA.get("aspect_categories",
                                               ['Restaurant#general', 'Service#general', 'Service#speed',
                                                'Food#quality', 'Food#prices', 'Food#style_options',
                                                'Ambience#general', 'Location#general', 'Drinks#quality',
                                                'Drinks#prices'])

        model_a_triplets = []
        model_b_triplets = []
        model_a_name = CONFIG_DATA.get("compare_model_a_name", "Model A")
        model_b_name = CONFIG_DATA.get("compare_model_b_name", "Model B")
        text_val = ""
        translation_val = ""
        label_val = ""
        aspects_val = default_aspects
        newui_data = None

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

            if "aspect_triplets" in row_dict:
                model_a_triplets = parse_triplet_column(row_dict.get("aspect_triplets"), prefix="ma")
            if "new_triplets" in row_dict:
                model_b_triplets = parse_triplet_column(row_dict.get("new_triplets"), prefix="mb")

            comp_a_path = CONFIG_DATA.get("compare_model_a_csv")
            comp_b_path = CONFIG_DATA.get("compare_model_b_csv")
            if comp_a_path or comp_b_path:
                if comp_a_path:
                    model_a_triplets = _load_comparison_csv(comp_a_path, data_idx, text_val, "ma")
                if comp_b_path:
                    model_b_triplets = _load_comparison_csv(comp_b_path, data_idx, text_val, "mb")

            # NEWUI 4-way comparison detection (Phase 7.1)
            newui_data = _load_4way_row(row, row_dict)

        agent_initial_reasoning = str(row_dict.get("reasoning", "")) if DATA_FILE_TYPE != "json" and "reasoning" in row_dict else ""
        if not agent_initial_reasoning or agent_initial_reasoning in ["nan", "None", ""]:
            agent_initial_reasoning = generate_mock_reasoning(text_val, model_a_name, model_b_name,
                                                              model_a_triplets, model_b_triplets)

        response = {
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

        if newui_data is not None:
            response["gt_triplets"] = newui_data["gt_triplets"]
            response["gemma_triplets"] = newui_data["gemma_triplets"]
            response["qwen_triplets"] = newui_data["qwen_triplets"]
            response["gpt_triplets"] = newui_data["gpt_triplets"]
            response["majority_vote"] = newui_data["majority_vote"]
            response["majority_label"] = newui_data["majority_label"]
            response["consensus_intersection"] = newui_data["consensus_intersection"]
            response["original_llm_diff"] = newui_data["original_llm_diff"]

        return response

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"{DATA_FILE_PATH} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/review/{data_idx}/save")
def save_review_triplets(data_idx: int, req: SaveTripletsRequest):
    """Save annotation triplets for a given row (the PRIMARY save endpoint)."""
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

        if req.review_text is not None:
            if DATA_FILE_TYPE == "json":
                if "review_text" in data[data_idx]:
                    data[data_idx]["review_text"] = req.review_text
                else:
                    data[data_idx]["text"] = req.review_text
                save_data(data)
            else:
                if "review_text" in df.columns:
                    df.at[data_idx, "review_text"] = req.review_text
                else:
                    df.at[data_idx, "text"] = req.review_text
                save_data(df)

        return {"status": "success", "message": "İnceleme tripletleri başarıyla kaydedildi.", "next_index": data_idx + 1}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/chat")
def agent_chat(req: AgentChatRequest):
    """Handle chat messages from the Helper Agent panel (POST /agent/chat)."""
    from services.prediction import DEFAULT_CHAT_TEMPLATE
    config = load_config()
    model_a_name = config.get("compare_model_a_name", "Model A")
    model_b_name = config.get("compare_model_b_name", "Model B")

    # Collect labeled examples for BM25 few-shot retrieval
    data = load_data()
    examples = []
    if DATA_FILE_TYPE == "json":
        for entry in data:
            lbl = entry.get('label', [])
            if isinstance(lbl, list) and lbl:
                examples.append({'text': entry.get('text', entry.get('review_text', '')), 'label': lbl})
    else:
        df = data
        for _, r in df.iterrows():
            lbl_str = r.get('label', '')
            if pd.isna(lbl_str) or lbl_str == '':
                continue
            try:
                lbl = json.loads(lbl_str) if isinstance(lbl_str, str) else lbl_str
                if isinstance(lbl, list) and lbl:
                    examples.append({'text': r.get('text', r.get('review_text', '')), 'label': lbl})
            except Exception:
                continue

    from services.prediction import get_most_similar_examples
    few_shot_results = get_most_similar_examples(req.review_text, examples, n=2)
    few_shot_str = ""
    for ex in few_shot_results:
        few_shot_str += f"Metin: {ex['text']}\nEtiketler: {ex['label']}\n\n"
    few_shot_str = few_shot_str.strip()

    agent_provider = CONFIG_DATA.get("helper_agent_provider") or None
    agent_model = CONFIG_DATA.get("helper_agent_model") or None
    agent_temperature = CONFIG_DATA.get("helper_agent_temperature", 0.7)

    chat_template = CONFIG_DATA.get("helper_agent_prompt") or CONFIG_DATA.get('helper_agent_prompt_template', DEFAULT_CHAT_TEMPLATE)
    system_content = chat_template.format(
        review_text=req.review_text,
        model_a_name=model_a_name,
        model_a_triplets=req.model_a_triplets,
        model_b_name=model_b_name,
        model_b_triplets=req.model_b_triplets,
        few_shot_examples=few_shot_str,
    )
    messages = [{"role": "system", "content": system_content}]
    for h in req.chat_history[-4:]:
        role = "assistant" if h.get("sender") == "agent" else "user"
        messages.append({"role": role, "content": h.get("text", "")})
    messages.append({"role": "user", "content": req.user_message})

    try:
        if agent_provider:
            provider_name = agent_provider
        else:
            provider_name = llm_providers._derive_provider(CONFIG_DATA)
        val_errors = llm_providers.validate_provider_config(provider_name, config)
        if val_errors:
            raise ValueError(val_errors[0])

        provider = llm_providers.get_provider(provider_name, CONFIG_DATA)
        reply = provider.chat(
            messages=messages,
            model=agent_model or config.get("llm_model", "gemma3:4b"),
            temperature=agent_temperature,
            max_tokens=300
        )
        return {"reply": reply}
    except Exception as e:
        print(f"Provider chat error: {e}")

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
