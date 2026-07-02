# Task 1 Kickoff — STD format dataset integration

This is the only task for this session. Full context below — everything you need is inlined,
you don't need to ask for other files unless something referenced here is missing.

## Task

STD format is a two-column CSV (`review,triplet`) used by our research group. Example
(`coursera_train.csv`):

```csv
review,triplet
"Çok az araştırma temeli olan harika ""amatör tavsiyeler"" sunuyordu.","[['NULL', 'presentation quality', 'negative']]"
Böylesine harika materyal için tüm yazarlara teşekkürler.,"[['materyal', 'material quality', 'positive']]"
Bu alana ilgi duyan herkese tavsiye ederim.,"[['NULL', 'course general', 'positive']]"
Giriş oturumu çok tekrarlıydı.,"[['NULL', 'presentation quality', 'negative']]"
İngilizce öğrenme ve öğretme konusunda bambaşka bir bakış açısı açtı.,"[['NULL', 'course general', 'positive']]"
Ayrıca son ödev talimatlarının biraz kafa karıştırıcı olduğunu düşündüm.,"[['ödev', 'assignments comprehensiveness', 'negative']]"
Bu muhteşemdi kurs.,"[['kurs', 'course general', 'positive']]"
"Daha da önemlisi, bu ders bana artık yeteneğim/ilgim olmasa bile öğrenme tutumuyla her şeyi öğrenebileceğime dair güven verdi.","[['ders', 'course relatability', 'positive']]"
"Bunların hepsini bildirdim ve tek bir yanıt bile alamadım, belki de bunun nedeni ödeme yapan bir müşteri olmamam olabilir.","[['NULL', 'faculty response', 'negative']]"
```

Rules:
- `review` = text to annotate.
- `triplet` = a **Python list-literal string** (single quotes, not JSON) of 3-element lists:
  `[aspect_term, aspect_category, sentiment_polarity]`.
- `aspect_term` is the literal string `'NULL'` when the aspect is implicit.
- No `opinion_term`, no character positions — STD only has these 3 fields.
- A review can have zero, one, or multiple triplets.

### The app's internal format (what everything else in the codebase expects)

A `label` field (CSV column, JSON-encoded string; or JSON-file key) holding a list of dicts:

```json
[{"aspect_term": "materyal", "aspect_category": "material quality", "sentiment_polarity": "positive", "opinion_term": "", "at_start": 0, "at_end": 0, "ot_start": 0, "ot_end": 0}]
```

### What to build

1. A converter function, e.g. `std_triplets_to_label(raw_triplet_str: str) -> list[dict]`:
   - `'NULL'` → `aspect_term: "NULL"` (keep the literal string — see the
     `auto_add_missing_positions` excerpt further down for why this matches the codebase's
     existing implicit-aspect convention; don't convert it to an empty string).
   - `opinion_term: ""`, omit/zero out position fields — don't invent positions here.
   - `[]` or empty/unparseable → `[]`. Don't crash the app on a malformed row — log and return
     `[]` (mirror the existing `parse_triplet_column`'s `try/except` pattern below).
2. A new CLI flag, `--format std`, so `annoabsa coursera_train.csv --format std` loads a STD
   file. Do NOT auto-detect format from column names — require the explicit flag. Wire this
   into `cli.py`'s argparse (see the existing flag patterns below) and pass it through to
   `main.py` (see how `data_path`/file extension is currently validated and used, below) so
   `load_data`/`set_data_file` know to run the STD→internal conversion at load time, not on
   every request.
3. Convert once at load time (into the working CSV format `load_data`/`save_data` already use)
   — don't add per-request branching in `get_data`/`post_annotations` for this.
4. An export path back to STD format: a CLI flag (e.g. `--export-std <output_path>`) or a
   small standalone script that takes the internal `label` format and writes `review,triplet`
   CSV rows back out, using `repr()` of a list of 3-tuples (or equivalent) so the output string
   round-trips via `ast.literal_eval` to the same structure as the input (doesn't need to be
   byte-identical). Only `aspect_term`/`aspect_category`/`sentiment_polarity` round-trip —
   `opinion_term`/positions are dropped on export, since STD doesn't have them.

### Edge cases — write a test/check for each

- Implicit aspect: `[['NULL', 'course general', 'positive']]`
- Multiple triplets in one review
- Empty triplet list: `[]` or empty string
- Embedded double quotes in review text (see the `"amatör tavsiyeler"` row above — standard
  CSV quoting, `pandas.read_csv` already handles this; don't reprocess the text yourself)
- Malformed/unparseable triplet string — must not crash, should log + return `[]`

### Definition of done

- Loading the 9-row sample above via `--format std` produces correct `text`/`label` for every
  row — verify against hand-written expected output for each row.
- A STD-loaded item, annotated and saved through `post_annotations` (unmodified), works.
- Export round-trips a small fixture (triplets only, not opinion_term/positions).

---

## Current source you need (exact, as of now — don't assume anything beyond this)

### `main.py` — global data-file-type switch (~L15-19)

```python
DATA_FILE_PATH = os.environ.get('ABSA_DATA_PATH', "annotations.csv")  # Default
DATA_FILE_TYPE = "json" if DATA_FILE_PATH.endswith('.json') else "csv"
```

### `main.py::load_data` / `save_data` (~L82-100)

```python
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
```

### `main.py::parse_triplet_column` (~L176-208) — existing parser for the same list-literal
syntax, currently only feeds the LLM-comparison columns (different task, different output
shape — don't reuse its output shape directly, but its `ast.literal_eval` parsing approach and
error handling is the pattern to mirror)

```python
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
```

Note: `ast` must already be imported at the top of `main.py` for this function to work —
confirm the import exists rather than assuming.

### `main.py::get_data` (~L241-325, relevant portion)

```python
@app.get("/data/{data_idx}")
def get_data(data_idx: int):
    try:
        data = load_data()
        if data_idx >= len(data) or data_idx < 0:
            raise HTTPException(status_code=404, detail="Index out of range")

        default_aspects = CONFIG_DATA.get("aspect_categories", [...])  # restaurant domain defaults

        deepseek_triplets = []
        qwen_triplets = []
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
            deepseek_triplets = item.get("deepseek_triplets", [])
            qwen_triplets = item.get("qwen_triplets", [])
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

            # Support user custom format: review_text, aspect_triplets, new_triplets, reasoning
            if "aspect_triplets" in row_dict:
                deepseek_triplets = parse_triplet_column(row_dict.get("aspect_triplets"), prefix="ds")
            if "new_triplets" in row_dict:
                qwen_triplets = parse_triplet_column(row_dict.get("new_triplets"), prefix="qw")

            # ... sibling-CSV fallback for deepseek/qwen triplets, not relevant to this task ...

        # ... returns dict with text, label, translation, aspect_category_list, etc.
```

Key point for this task: `get_data` reads `text_val` from `review_text` or `text` column, and
`label_val` from a `label` column — **already**. So if your STD→internal conversion at load
time renames `review`→`review_text` (or `text`) and `triplet`→`label` (converted), `get_data`
should work unmodified. Verify this end-to-end rather than assuming.

### `main.py::post_annotations` (~L400-420) — unmodified, confirm it Just Works

```python
@app.post("/annotations/{data_idx}")
def post_annotations(data_idx: int, annotation_data: AnnotationData):
    try:
        data = load_data()
        if data_idx >= len(data) or data_idx < 0:
            raise HTTPException(status_code=404, detail="Index out of range")

        annotation_data = annotation_data.value

        if DATA_FILE_TYPE == "json":
            data[data_idx]['label'] = annotation_data
            save_data(data)
        else:
            df = data
            annotations_json = json.dumps(annotation_data)
            df.at[data_idx, 'label'] = annotations_json
            save_data(df)

        return {"message": "Annotations saved successfully"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"{DATA_FILE_PATH} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### `cli.py` — relevant argparse flags already present (~L393-463, excerpt showing the pattern
to follow for the new `--format` flag)

```python
    parser.add_argument(
        "data_path",
        help="Path to the CSV or JSON file containing the data to annotate"
    )

    parser.add_argument(
        "--session-id",
        help="Optional session ID to identify this annotation session"
    )

    parser.add_argument(
        "--elements",
        nargs="+",
        choices=["aspect_term", "aspect_category", "sentiment_polarity", "opinion_term"],
        help="Sentiment elements to annotate (default: all four elements)"
    )

    parser.add_argument(
        "--polarities",
        nargs="+",
        help="Available sentiment polarities (default: positive, negative, neutral)"
    )

    parser.add_argument(
        "--categories",
        nargs="+",
        help="Available aspect categories (default: restaurant domain categories)"
    )

    parser.add_argument(
        "--implicit-aspect",
        action="store_true",
        default=True,
        help="Allow implicit aspect terms (default: True)"
    )

    # ... more flags follow the same pattern (action="store_true" or nargs="+") ...
```

### `cli.py` — how `data_path` / file type is currently validated before backend start (~L580-599)

```python
    args = parser.parse_args()

    # Check if data file exists
    if not os.path.exists(args.data_path):
        print(f"❌ Error: Data file '{args.data_path}' not found!")
        sys.exit(1)

    # Check file format
    file_extension = os.path.splitext(args.data_path)[1].lower()
    if file_extension not in ['.csv', '.json']:
        print(
            f"❌ Error: Unsupported file format '{file_extension}'. Use .csv or .json files.")
        sys.exit(1)

    print(f"📂 Using {file_extension[1:].upper()} file: {args.data_path}")
    if file_extension == '.csv':
        print("💡 Note: CSV file will be read/written with UTF-8 encoding")

    # Initialize configuration
    config = ABSAAnnotatorConfig(args.data_path)
```

Your new `--format std` flag needs to hook in around here — see the exact mechanism and
recommendation below (the answer to your questions).

### `main.py::set_data_file` and the data-file-path wiring mechanism (~L18, L36-40)

This confirms the actual mechanism: **environment variable, read once at module import time**
— not a runtime re-assignment call from the CLI process, and `set_data_file` is not currently
invoked anywhere in the CLI→backend startup path (it exists in `main.py` but nothing calls it
today; the module-level line at import time is what actually sets `DATA_FILE_PATH`).

```python
# main.py, ~L18 (module-level, runs once at import)
DATA_FILE_PATH = os.environ.get('ABSA_DATA_PATH', "annotations.csv")  # Default
DATA_FILE_TYPE = "json" if DATA_FILE_PATH.endswith('.json') else "csv"

# main.py, ~L36-40
def set_data_file(file_path: str):
    """Set the data file path and determine file type."""
    global DATA_FILE_PATH, DATA_FILE_TYPE
    DATA_FILE_PATH = file_path
    DATA_FILE_TYPE = "json" if file_path.endswith('.json') else "csv"
```

### `cli.py::start_backend` — how the env var actually gets set before the backend subprocess starts (~L228-252)

```python
def start_backend(port: int = 8000, host: str = "localhost", data_path: str = None, config: ABSAAnnotatorConfig = None):
    """Start the FastAPI backend server."""
    global backend_process
    try:
        if is_port_in_use(host, port):
            print(f"⚠️  Port {port} is already in use on {host}")
            print(f"💡 Backend might already be running on http://{host}:{port}")
            return

        print(f"🚀 Starting backend server on {host}:{port}...")
        if data_path:
            os.environ['ABSA_DATA_PATH'] = data_path
        if config:
            # Save config to temporary file for backend to read
            config_file = "temp_absa_config.json"
            config.save_config(config_file)
            os.environ['ABSA_CONFIG_PATH'] = config_file

        backend_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn",
            "main:app", "--reload", f"--port={port}", f"--host={host}"
        ])
        # ... process wait/cleanup, not relevant here ...
```

**This is the key mechanism**: `cli.py` sets `os.environ['ABSA_DATA_PATH']` to the raw
`args.data_path` *before* spawning `uvicorn` as a subprocess, which inherits the env var.
`main.py` reads it once at import. There is **no IPC after that point** — no re-reading of the
CLI's `args`, no live config sync beyond this one env var and the equivalent
`ABSA_CONFIG_PATH` temp-file mechanism shown above (`config.save_config()` writes a temp JSON;
the backend reads it separately at its own import time via `CONFIG_PATH`/`CONFIG_DATA`, not
shown in full here but same shape).

**Implication for `--format std`**: since `main.py` never re-parses `data_path` itself, you
have two realistic options:

- **(A) Convert before spawning the subprocess.** In `cli.py`, when `--format std` is passed,
  read the original STD CSV, run the STD→internal conversion, write the result to a working
  file (e.g. a temp path), and set `os.environ['ABSA_DATA_PATH']` to point at *that* converted
  file instead of the original. `main.py` needs **zero changes** — it never knows the original
  was STD format. This matches the existing `ABSA_CONFIG_PATH` temp-file precedent above.
- **(B) Pass format via a second env var** (`ABSA_DATA_FORMAT=std`) and have `main.py` run the
  conversion itself at import time. This means `main.py` changes, and `load_data`/`save_data`
  would need to keep converting on every load/save unless you also write back a converted
  file — more invasive, duplicates the work Option A does once.

**Use Option A.** Convert once, in `cli.py`, write a working copy, point `ABSA_DATA_PATH` at
it. Zero `main.py` changes for the loading path — only the separate export flag/script touches
STD format after that.

### `main.py::auto_add_missing_positions` (~L485-560, full function — corrects an earlier assumption in this doc)

```python
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
            for item in data:
                if 'text' not in item:
                    continue

                text = item['text']
                label_data = item.get('label', [])

                if isinstance(label_data, str):
                    if not label_data or label_data == '':
                        continue
                    try:
                        annotations = json.loads(label_data)
                    except (json.JSONDecodeError, TypeError):
                        continue
                else:
                    annotations = label_data

                if not isinstance(annotations, list):
                    continue

                annotations_updated = False

                for annotation in annotations:
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
                    item['label'] = annotations
                    data_changed = True
        else:
            # CSV format branch: same logic, iterating df.iterrows(), same 'NULL' checks —
            # symmetric to the JSON branch above, omitted here since it adds no new information
            ...
        # ... saves data_changed, prints updated_count, not relevant to this task ...
```

**This corrects something stated earlier in this doc.** The task text above said the STD
converter should map `'NULL'` → `aspect_term: ""` (empty string). That's **wrong** — this
function's own convention is `!= 'NULL'` (the literal string) as the "has a real span" check.
It never converts `'NULL'` to `""` anywhere; it just skips position-finding when the term
equals `'NULL'`. If your converter instead emitted `""`, this function's check
(`annotation['aspect_term'] and annotation['aspect_term'] != 'NULL'`) would still be truthy
for `""`... no — actually `""` is falsy in Python, so `annotation['aspect_term']` alone would
already be `False` for an empty string, meaning the check would correctly skip it too. So
either representation happens to avoid breaking *this specific function*. But `""` is still
the wrong choice, because **other code paths check equality against `'NULL'` specifically**
(e.g. this function's own `!= 'NULL'` pattern is the codebase's established convention for
"implicit," and any future code — including your own STD export function — that needs to
detect "is this an implicit aspect" should be able to check `== 'NULL'` consistently). Use the
literal string `"NULL"` for `aspect_term` when the STD source has `'NULL'`, not `""`. This
keeps the internal format consistent with the codebase's existing convention rather than
introducing a second way of representing the same thing.

### `cli.py::ABSAAnnotatorConfig` — full class (~L50-215)

```python
class ABSAAnnotatorConfig:
    """Configuration manager for AnnoABSA."""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.config = {
            "csv_path": csv_path,
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
            "auto_positions": False,
            "store_time": False,
            "display_avg_annotation_time": False,
            "enable_pre_prediction": False,
            "disable_ai_automatic_prediction": False,
            "annotation_guideline": None,
            "n_few_shot": 10,
            "openai_key": None
        }

    # ... one setter method per config key above (set_sentiment_elements, set_aspect_categories,
    #     set_implicit_aspect_allowed, etc.) — straightforward, omitted since none are relevant
    #     to STD format loading ...

    def get_config(self) -> Dict[str, Any]:
        return self.config.copy()

    def save_config(self, output_path: str = "absa_config.json") -> None:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        print(f"✅ Configuration saved to {output_path}")

    def load_config(self, config_path: str) -> None:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
            for key, value in loaded_config.items():
                if key in self.config:
                    self.config[key] = value
            print(f"✅ Configuration loaded from {config_path}")
        except FileNotFoundError:
            print(f"❌ Configuration file '{config_path}' not found!")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in configuration file: {e}")
            sys.exit(1)
```

**Key point**: `csv_path` is stored on the config object, but `start_backend` (above) takes
`data_path` as a **separate argument**, not from `config.get_config()['csv_path']`. This
confirms: the data file path and your new format flag are CLI-argument concerns, handled in
the argparse/main-execution block (~L580-599, shown earlier), and in `start_backend`'s
`os.environ['ABSA_DATA_PATH'] = data_path` line — not in `ABSAAnnotatorConfig`. You don't need
to add anything to this class for this task.

---

## What I need from you

1. A plan in the step→verify format from the primer.
2. Wait for my go-ahead.
3. Then full file contents (or clearly marked diffs) for every file you change.

If you need to see more of `main.py` or `cli.py` than what's pasted above (e.g. the full
argparse block, or how `ABSAAnnotatorConfig` uses `data_path`), ask me for it by name/line
range rather than assuming its shape.