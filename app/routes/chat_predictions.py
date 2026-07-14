"""Chat predictions endpoint — GET /chat/predictions/{data_idx}.

Returns ML predictions formatted as natural Turkish text that the Helper Agent
can read, reason about, and act on. Also returns raw predictions for
programmatic use.
"""
from fastapi import APIRouter, HTTPException

from app.config import CONFIG_DATA, DATA_FILE_TYPE
from app.data import load_data
from services.active_learning import (
    labeled_texts_from_data,
    train_labeled_data,
)

router = APIRouter(tags=["chat_predictions"])


def _get_file_type() -> str:
    """Resolve the effective file type from config or global default."""
    return CONFIG_DATA.get("DATA_FILE_TYPE", DATA_FILE_TYPE)


@router.get("/chat/predictions/{data_idx}")
def get_chat_predictions(data_idx: int):
    """Return ML predictions for a single review as chat-formatted text.

    Returns both a Turkish text paragraph (for the Helper Agent to read)
    and the raw predictions array (for programmatic use).

    Parameters
    ----------
    data_idx : int
        0-based index of the review to predict.

    Returns
    -------
    dict
        ``{'text': str, 'predictions': list[dict]}`` where each prediction
        has keys ``aspect_category``, ``sentiment_polarity``, ``confidence``,
        ``label``.
    """
    try:
        data = load_data()
        file_type = _get_file_type()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading data: {str(e)}")

    if data_idx < 0 or (file_type == "json" and data_idx >= len(data)) or (file_type != "json" and data_idx >= len(data)):
        raise HTTPException(status_code=404, detail=f"Index {data_idx} out of range.")

    texts, label_sets = labeled_texts_from_data(data, file_type)

    # Only keep reviews with labels for training
    labeled_texts = [texts[i] for i in range(len(texts)) if label_sets[i]]
    labeled_labels = [label_sets[i] for i in range(len(texts)) if label_sets[i]]

    if len(labeled_texts) < 2:
        raise HTTPException(
            status_code=400,
            detail="Not enough labeled reviews (need at least 2) to generate predictions.",
        )

    model_data = train_labeled_data(labeled_texts, labeled_labels)
    if model_data is None:
        raise HTTPException(status_code=400, detail="Failed to train model.")

    model = model_data["model"]
    label_columns = model_data["label_columns"]

    target_text = texts[data_idx]
    proba = model.predict_proba([target_text])

    # Build predictions list
    predictions = []
    for col_idx, col_name in enumerate(label_columns):
        p_pos = float(proba[0, col_idx])
        parts = col_name.rsplit("__", 1)
        category, polarity = parts if len(parts) == 2 else (col_name, "")
        predictions.append({
            "aspect_category": category,
            "sentiment_polarity": polarity,
            "confidence": float(round(p_pos, 6)),
            "label": col_name,
        })

    # Sort by confidence descending
    predictions.sort(key=lambda x: x["confidence"], reverse=True)

    # Build Turkish chat text
    high_conf = [p for p in predictions if p["confidence"] > 0.5]
    if not high_conf:
        text = (
            f"Bu inceleme için yüksek güvenli tahmin bulunamadı. "
            f"En yakın tahminler:\n"
        )
        for p in predictions[:3]:
            text += (
                f"- Kategori: {p['aspect_category']}, "
                f"Kutup: {p['sentiment_polarity']} "
                f"(güven: {p['confidence']:.2f})\n"
            )
        text += "\nDaha fazla etiketlenmiş inceleme toplandıkça tahmin kalitesi artacaktır."
    else:
        lines = ["Modelin bu inceleme için tahminleri:"]
        for p in high_conf:
            lines.append(
                f"- Kategori: {p['aspect_category']}, "
                f"Kutup: {p['sentiment_polarity']} "
                f"(güven: {p['confidence']:.2f})"
            )
        lines.append("")
        lines.append(
            "Yüksek güvenli tahminleri seçip kaydedebilir "
            "veya manuel olarak düzenleyebilirsiniz."
        )
        text = "\n".join(lines)

    return {
        "text": text,
        "predictions": predictions,
    }
