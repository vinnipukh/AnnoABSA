"""Prediction-related utilities — prompt building, BM25 retrieval, position logic.

Moved from main.py during root reorganization (Step 4).
All functions are pure (no main.py globals), operating on passed-in parameters.
"""
import re
import json
import numpy as np
from enum import Enum
from pydantic import BaseModel, create_model
try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

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


def generate_mock_reasoning(text: str, model_a_name: str, model_b_name: str, model_a_list: list, model_b_list: list) -> str:
    """Generate a Turkish-language reasoning paragraph comparing two model outputs.

    Produces a human-readable analysis noting common aspects, model-specific
    differences, and a recommendation. Used as fallback when the CSV doesn't
    have a pre-computed 'reasoning' column, or when the backend's LLM-based
    helper agent isn't available.

    Args:
        text: The review text being analyzed.
        model_a_name: Display name for Model A (e.g. 'Model A' or 'GPT-4o').
        model_b_name: Display name for Model B.
        model_a_list: List of triplet dicts from Model A (keys: aspect_term, ...).
        model_b_list: List of triplet dicts from Model B.

    Returns:
        A string containing the Turkish analysis paragraph.
    """
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




def get_most_similar_examples(input_text, examples, n):
    """Return up to n most similar examples via BM25 retrieval.

    Tokenizes with lowercase \\w+ regex (no Turkish stemming).
    Returns top-n sorted by BM25 similarity descending.
    Returns all if n >= len(examples).

    Args:
        input_text: The text to find similar examples for.
        examples: List of dicts with {'text': ..., 'label': ...}.
        n: Max examples to return.

    Returns:
        List of up to n examples, most similar first.
    """

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
        """Simple tokenizer: lowercase, split on word boundaries."""
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
    """Enumerate all valid sub-phrases from text up to a max token count.

    Splits at punctuation/whitespace boundaries, enumerates all contiguous
    sub-phrases. Filters out those starting/ending with non-word characters.

    Used by build_absa_models() to create allowed aspect/opinion terms
    for Pydantic enum generation (structured LLM output).

    Args:
        text: The review text.
        max_tokens_in_phrase: Max word count (None = unlimited).

    Returns:
        List of valid phrase strings.
    """
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
        """Container for a list of SentimentElement predictions."""
        aspects: list['SentimentElement']

    return Aspects, field_types, {"AspectEnum": AspectEnum, "OpinionEnum": OpinionEnum, "PolarityEnum": PolarityEnum, "CategoryEnum": CategoryEnum}
