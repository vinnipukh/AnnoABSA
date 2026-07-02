Task 4 Kickoff — Helper Agent Prompt Improvements

This is the only task for this session. Full context is below. Read carefully before proposing a plan.
Task

The current prompts (both for structured labeling and the conversational helper agent) are hardcoded, duplicated across multiple functions, and written in English. Your job is to make these prompts Turkish-language, user-configurable (via the existing JSON config system), and consolidated (removed from provider logic).
Scope & Constraints (Strict)

    Language: The instruction prose must be in Turkish.

    Categorization: aspect_category and sentiment_polarity values must stay in English (e.g., positive, food quality). Do NOT translate these strings; the models must output the English labels regardless of the Turkish instruction language.

    Configurability: The prompts must be stored in the config JSON (loaded at startup) and not hardcoded in Python literals.

    Scope: This applies to both the Labeling Prompt (used by all 4 providers) and the Helper Agent Chat Prompt.

Current state (Verify before coding)

    Labeling Prompt: Duplicated logic exists inside the predict() methods of the four provider adapters.

    Helper Agent Prompt: Currently a hardcoded f-string in agent_chat() (~L1140). It references the old hardcoded "DeepSeek"/"Qwen" names, which Task 2/3 refactored.

    Configuration: You have existing JSON config infrastructure; this task extends it with two new keys: labeling_prompt_template and helper_agent_prompt_template.

What to build

    Config Expansion: Add the two template strings to the default configuration in main.py::load_config().

    Prompt Consolidation:

        Factor prompt construction out of the four provider adapters into a single shared helper function in main.py (or a dedicated prompts.py if cleaner).

        This function should accept a template string and appropriate placeholders (e.g., text, aspect_categories, polarities, few_shot_examples) and return the final string.

    Template Implementation:

        Use the following default Turkish Labeling Prompt:
        Plaintext

        Aşağıdaki duygu unsuru tanımlarına göre:

        - 'aspect term' (görünüş terimi), kullanıcının bir ürün veya hizmetin belirli bir özelliği hakkında görüş belirttiği, metindeki tam kelime veya kelime öbeğidir. {implicit_aspect_note}
        - 'aspect category' (görünüş kategorisi), görünüşün ait olduğu kategoridir. Mevcut kategoriler (bu kategori adlarını İngilizce olduğu gibi bırakın, çevirmeyin): {aspect_categories}
        - 'sentiment polarity' (duygu kutbu), ifade edilen görüşün olumluluk, olumsuzluk ya da nötrlük derecesidir. Mevcut kutuplar (İngilizce olduğu gibi bırakın, çevirmeyin): {polarities}
        - 'opinion term' (görüş terimi), kullanıcının bir görünüşe yönelik tutumunu ifade eden, metindeki tam kelime veya kelime öbeğidir. {implicit_opinion_note}

        Metin Türkçedir ve Türkçe sondan eklemeli (agglutinative) bir dildir: aynı kök farklı çekim ekleriyle görünebilir (ör. "kitap", "kitabı", "kitaplarımdan"). Görünüş ve görüş terimlerini ararken kelimenin metindeki tam, çekimli halini seçin — kökü ayırıp yeniden yazmayın.

        Aşağıdaki metindeki tüm duygu unsurlarını, karşılık gelen {element_names} ile birlikte, her biri {element_keys} anahtarlarına sahip nesnelerden oluşan bir liste biçiminde tanıyın.

    Helper Agent Chatbox Update:

        Refactor agent_chat() to load the chat prompt from the config.

        Ensure it dynamically injects the model display names (defined in config) into the chat prompt so it no longer uses hardcoded strings.

    Validation: Ensure the logic safely handles missing keys in the config file by falling back to the defaults.

Definition of done

    Running the Helper Agent chatbox shows a Turkish system prompt.

    Prediction outputs from all 4 providers correctly use the new Turkish instructions while maintaining the English aspect_category and sentiment_polarity values.

    Changing the template string in the config JSON immediately updates the model's behavior on the next run.

    The hardcoded "DeepSeek"/"Qwen" strings are completely eliminated from main.py.

What I need from you

    A step-by-step execution plan in the [Step] → verify: [how I'll check this worked] format.

    Wait for my go-ahead.

    Once approved, provide the full file contents (or clearly marked diffs) for every file you change.

If you need to see the main.py logic for agent_chat() or the current prompt logic in the provider adapters before formulating your plan, ask me for it now.