"""NLP Helper Toolbar endpoints.

Endpoints:
    GET /nlp/lexicon-polarity      — per-word sentiment lookup (SentiNet)
    GET /nlp/sentiment             — sentence-level sentiment classification (BERT)
    GET /nlp/morphology            — morphological analysis (NlpToolkit)
    GET /nlp/embedding-similarity  — cosine similarity (e5-small)
"""
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/nlp", tags=["nlp"])


@router.get("/lexicon-polarity")
def get_lexicon_polarity(text: str):
    """Per-word sentiment polarity lookup via SentiNet lexicon."""
    try:
        from services.nlp_helpers import lexicon_polarity as _lp
        return _lp(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lexicon error: {str(e)}")


@router.get("/sentiment")
def get_sentiment(text: str):
    """Sentence-level sentiment classification via BERT."""
    try:
        from services.nlp_helpers import sentiment_classify as _sc
        return _sc(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sentiment error: {str(e)}")


@router.get("/morphology")
def get_morphology(word: str):
    """Morphological analysis of a single word via NlpToolkit."""
    try:
        from services.nlp_helpers import morphology as _mo
        return _mo(word)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Morphology error: {str(e)}")


@router.get("/embedding-similarity")
def get_embedding_similarity(selection: str, sentence: str):
    """Cosine similarity between selected span and full sentence via e5-small."""
    try:
        from services.nlp_helpers import embedding_similarity as _es
        return _es(selection, sentence)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding error: {str(e)}")
