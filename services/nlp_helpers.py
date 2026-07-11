"""NLP Helper Toolbar — lazy-loaded tools.

Four lazy-loaded NLP tools for the NLP Helper Toolbar:
1. Word-level sentiment (SentiNet lexicon via WordNet flattening)
2. Sentence-level sentiment (HuggingFace BERT classifier)
3. Morphological analysis (NlpToolkit FsmMorphologicalAnalyzer)
4. Embedding similarity (multilingual-e5-small)

All loaded lazily (first-use only). No imports at module level.
"""

import numpy as np

# Module-level lazy-load caches
_sentinet = None
_sentiment_classifier = None
_morphological_analyzer = None
_embedding_model = None
_lexicon_dict = None


def get_sentinet():
    global _sentinet
    if _sentinet is None:
        from SentiNet.SentiNet import SentiNet
        _sentinet = SentiNet()
    return _sentinet


def get_sentiment_classifier():
    global _sentiment_classifier
    if _sentiment_classifier is None:
        from transformers import pipeline
        _sentiment_classifier = pipeline(
            "sentiment-analysis",
            model="savasy/bert-base-turkish-sentiment-cased",
            tokenizer="savasy/bert-base-turkish-sentiment-cased"
        )
    return _sentiment_classifier


def get_morphological_analyzer():
    global _morphological_analyzer
    if _morphological_analyzer is None:
        from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer
        _morphological_analyzer = FsmMorphologicalAnalyzer()
    return _morphological_analyzer


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer('intfloat/multilingual-e5-small')
    return _embedding_model


def get_lexicon():
    global _lexicon_dict
    if _lexicon_dict is None:
        _lexicon_dict = _build_flattened_lexicon()
    return _lexicon_dict


def _clean_literal_name(name: str) -> str:
    """Strip parentheses and special chars from WordNet literal names.

    WordNet literal names look like '(güzel)' or '(yemek)' — strip the
    outer parentheses for a clean word. Also handles multi-word cases.
    """
    name = name.strip()
    if name.startswith('(') and name.endswith(')'):
        name = name[1:-1]
    # Remove leading/trailing non-alphanumeric (except Turkish chars)
    name = name.strip('«»"''`.,;:!?')
    return name.lower()


def _build_flattened_lexicon() -> dict:
    """Build {word: (polarity, score)} dict by iterating WordNet synsets.

    For each synset in WordNet, look up its polarity in SentiNet.
    If a word appears in multiple synsets with different polarities,
    average the scores and pick the dominant polarity label.
    """
    from WordNet.WordNet import WordNet
    sentinet = get_sentinet()
    wn = WordNet()
    lexicon = {}

    for synset in wn.synSetList():
        synset_id = synset.getId()
        try:
            ss = sentinet.getSentiSynSet(synset_id)
        except KeyError:
            # Synset not in SentiNet — skip
            continue
        if ss is None:
            continue

        pos_score = float(ss.getPositiveScore())
        neg_score = float(ss.getNegativeScore())

        if pos_score > neg_score:
            polarity = "positive"
            score = pos_score
        elif neg_score > pos_score:
            polarity = "negative"
            score = neg_score
        else:
            polarity = "neutral"
            score = 0.0

        synonym = synset.getSynonym()
        for i in range(synonym.literalSize()):
            raw_word = synonym.getLiteral(i).getName()
            word = _clean_literal_name(raw_word)
            if not word:
                continue

            if word in lexicon:
                existing_pol, existing_score = lexicon[word]
                new_score = (existing_score + score) / 2
                lexicon[word] = (
                    "positive" if new_score > 0
                    else "negative" if new_score < 0
                    else "neutral",
                    new_score
                )
            else:
                lexicon[word] = (polarity, score)

    return lexicon


def lexicon_polarity(text: str) -> dict:
    """Per-word sentiment lookup from SentiNet.

    Returns:
        {"words": [{"word": str, "polarity": str, "score": float}],
         "aggregate": str}
    """
    lexicon = get_lexicon()
    tokens = [w.strip(".,!?;:\"'()[]«»").lower() for w in text.split()]
    results = []
    for token in tokens:
        if not token:
            continue
        entry = lexicon.get(token)
        if entry:
            results.append({
                "word": token,
                "polarity": entry[0],
                "score": round(entry[1], 4)
            })
        else:
            results.append({
                "word": token,
                "polarity": "unknown",
                "score": 0.0
            })

    # Aggregate: majority polarity among known words
    known = [r for r in results if r["polarity"] != "unknown"]
    if known:
        from collections import Counter
        agg = Counter(r["polarity"] for r in known).most_common(1)[0][0]
    else:
        agg = "neutral"

    return {"words": results, "aggregate": agg}


def sentiment_classify(text: str) -> dict:
    """Sentence-level sentiment classification via HuggingFace.

    Returns:
        {"label": "positive"|"negative"|"neutral", "score": float}
    """
    classifier = get_sentiment_classifier()
    result = classifier(text, truncation=True, max_length=512)[0]
    return {
        "label": result["label"].lower(),
        "score": round(result["score"], 4)
    }


def morphology(word: str) -> dict:
    """Morphological analysis of a single word via NlpToolkit.

    Returns:
        {"word": str, "parses": [{"root": str, "ig": [str], "pos": str}]}
    """
    analyzer = get_morphological_analyzer()
    result = analyzer.morphologicalAnalysis(word)
    parses = []
    for i in range(result.size()):
        parse = result.getFsmParse(i)
        root = str(parse.getWord()).split()[0] if " " in str(parse.getWord()) else str(parse.getWord())
        ig_count = parse.size()
        igs = []
        for j in range(ig_count):
            ig = parse.getInflectionalGroup(j)
            igs.append(str(ig))
        first_ig = parse.getInflectionalGroup(0) if ig_count > 0 else None
        pos = str(first_ig).split("+")[0] if first_ig else "?"
        parses.append({
            "root": root,
            "ig": igs,
            "pos": pos
        })

    return {"word": word, "parses": parses}


def embedding_similarity(selection: str, sentence: str) -> dict:
    """Cosine similarity between selected span and full sentence.

    Returns:
        {"similarity": float (0.0-1.0), "selection_length": int}
    """
    model = get_embedding_model()
    emb_sel = model.encode("query: " + selection)
    emb_sent = model.encode("passage: " + sentence)
    sim = float(np.dot(emb_sel, emb_sent) /
                (np.linalg.norm(emb_sel) * np.linalg.norm(emb_sent)))
    return {
        "similarity": round(sim, 4),
        "selection_length": len(selection)
    }
