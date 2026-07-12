"""Review data endpoints — GET /data/{idx}, POST /review/{idx}/save, POST /agent/chat."""
from fastapi import APIRouter, HTTPException
import main
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
        data = main.load_data()
        if data_idx >= len(data) or data_idx < 0:
            raise HTTPException(status_code=404, detail="Index out of range")

        default_aspects = main.CONFIG_DATA.get("aspect_categories",
                                               ['Restaurant#general', 'Service#general', 'Service#speed',
                                                'Food#quality', 'Food#prices', 'Food#style_options',
                                                'Ambience#general', 'Location#general', 'Drinks#quality',
                                                'Drinks#prices'])

        model_a_triplets = []
        model_b_triplets = []
        model_a_name = main.CONFIG_DATA.get("compare_model_a_name", "Model A")
        model_b_name = main.CONFIG_DATA.get("compare_model_b_name", "Model B")
        text_val = ""
        translation_val = ""
        label_val = ""
        aspects_val = default_aspects

        if main.DATA_FILE_TYPE == "json":
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
                model_a_triplets = main.parse_triplet_column(row_dict.get("aspect_triplets"), prefix="ma")
            if "new_triplets" in row_dict:
                model_b_triplets = main.parse_triplet_column(row_dict.get("new_triplets"), prefix="mb")

            comp_a_path = main.CONFIG_DATA.get("compare_model_a_csv")
            comp_b_path = main.CONFIG_DATA.get("compare_model_b_csv")
            if comp_a_path or comp_b_path:
                if comp_a_path:
                    model_a_triplets = main._load_comparison_csv(comp_a_path, data_idx, text_val, "ma")
                if comp_b_path:
                    model_b_triplets = main._load_comparison_csv(comp_b_path, data_idx, text_val, "mb")

        agent_initial_reasoning = str(row_dict.get("reasoning", "")) if main.DATA_FILE_TYPE != "json" and "reasoning" in row_dict else ""
        if not agent_initial_reasoning or agent_initial_reasoning in ["nan", "None", ""]:
            agent_initial_reasoning = generate_mock_reasoning(text_val, model_a_name, model_b_name,
                                                              model_a_triplets, model_b_triplets)

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
        raise HTTPException(status_code=404, detail=f"{main.DATA_FILE_PATH} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/review/{data_idx}/save")
def save_review_triplets(data_idx: int, req: SaveTripletsRequest):
    """Save annotation triplets for a given row (the PRIMARY save endpoint)."""
    try:
        data = main.load_data()
        if data_idx >= len(data) or data_idx < 0:
            raise HTTPException(status_code=404, detail="Index out of range")

        triplets_list = req.triplets
        if main.DATA_FILE_TYPE == "json":
            data[data_idx]["label"] = triplets_list
            main.save_data(data)
        else:
            df = data
            triplets_json = json.dumps(triplets_list, ensure_ascii=False)
            df.at[data_idx, "label"] = triplets_json
            main.save_data(df)

        if req.review_text is not None:
            if main.DATA_FILE_TYPE == "json":
                if "review_text" in data[data_idx]:
                    data[data_idx]["review_text"] = req.review_text
                else:
                    data[data_idx]["text"] = req.review_text
                main.save_data(data)
            else:
                if "review_text" in df.columns:
                    df.at[data_idx, "review_text"] = req.review_text
                else:
                    df.at[data_idx, "text"] = req.review_text
                main.save_data(df)

        return {"status": "success", "message": "İnceleme tripletleri başarıyla kaydedildi.", "next_index": data_idx + 1}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/chat")
def agent_chat(req: AgentChatRequest):
    """Handle chat messages from the Helper Agent panel (POST /agent/chat)."""
    from services.prediction import DEFAULT_CHAT_TEMPLATE
    config = main.load_config()
    model_a_name = config.get("compare_model_a_name", "Model A")
    model_b_name = config.get("compare_model_b_name", "Model B")

    agent_provider = main.CONFIG_DATA.get("helper_agent_provider") or None
    agent_model = main.CONFIG_DATA.get("helper_agent_model") or None
    agent_temperature = main.CONFIG_DATA.get("helper_agent_temperature", 0.7)

    chat_template = main.CONFIG_DATA.get("helper_agent_prompt") or main.CONFIG_DATA.get('helper_agent_prompt_template', DEFAULT_CHAT_TEMPLATE)
    system_content = chat_template.format(
        review_text=req.review_text,
        model_a_name=model_a_name,
        model_a_triplets=req.model_a_triplets,
        model_b_name=model_b_name,
        model_b_triplets=req.model_b_triplets,
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
            provider_name = llm_providers._derive_provider(main.CONFIG_DATA)
        val_errors = llm_providers.validate_provider_config(provider_name, config)
        if val_errors:
            raise ValueError(val_errors[0])

        provider = llm_providers.get_provider(provider_name, main.CONFIG_DATA)
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
