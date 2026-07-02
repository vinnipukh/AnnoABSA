#!/usr/bin/env python3
"""
ABSA Annotation Tool CLI
A command-line interface for configuring and running AnnoABSA.
"""

import argparse
import json
import sys
import os
import subprocess
import threading
import time
import socket
import signal
import atexit
from typing import Dict, Any, List
from typing import List, Dict, Any
import ast
import pandas as pd

# ── Prompt template defaults (mirrored from main.py to avoid import-time side effects) ──

CLI_DEFAULT_LABELING_TEMPLATE = (
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

CLI_DEFAULT_CHAT_TEMPLATE = (
    'Sen ABSA (Aspect-Based Sentiment Analysis) veri etiketleme asistanısın. '
    'Şu incelemeyi tartışıyorsunuz: "{review_text}". '
    '{model_a_name} tripletleri: {model_a_triplets}, '
    '{model_b_name} tripletleri: {model_b_triplets}. '
    "Kullanıcıya mantıklı, akıl yürüterek açıklama yap."
)

# Global variable to track backend process
backend_process = None
shutdown_flag = threading.Event()


def cleanup_backend():
    """Clean up backend process on exit."""
    global backend_process
    if backend_process and backend_process.poll() is None:
        print("\n🧹 Cleaning up backend process...")
        backend_process.terminate()
        try:
            backend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend_process.kill()


def signal_handler(signum, frame):
    """Handle interrupt signals."""
    print("\n🛑 Received interrupt signal. Shutting down...")
    shutdown_flag.set()
    cleanup_backend()


# Register cleanup functions
atexit.register(cleanup_backend)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


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
            "llm_provider": None,
            "llm_model": "gemma3:4b",
            "openai_key": None,
            "anthropic_key": None,
            "vllm_url": None,
            "vllm_model": None,
            "compare_model_a_csv": None,
            "compare_model_a_name": None,
            "compare_model_b_csv": None,
            "compare_model_b_name": None,
            "labeling_prompt_template": CLI_DEFAULT_LABELING_TEMPLATE,
            "helper_agent_prompt_template": CLI_DEFAULT_CHAT_TEMPLATE
        }

    def set_sentiment_elements(self, elements: List[str]) -> None:
        """Set the sentiment elements to annotate."""
        valid_elements = ["aspect_term", "aspect_category",
                          "sentiment_polarity", "opinion_term"]
        for element in elements:
            if element not in valid_elements:
                raise ValueError(
                    f"Invalid sentiment element: {element}. Valid options: {valid_elements}")
        self.config["sentiment_elements"] = elements

    def set_sentiment_polarities(self, polarities: List[str]) -> None:
        """Set the available sentiment polarities."""
        self.config["sentiment_polarity_options"] = polarities

    def set_aspect_categories(self, categories: List[str]) -> None:
        """Set the available aspect categories."""
        self.config["aspect_categories"] = categories

    def set_implicit_aspect_allowed(self, allowed: bool) -> None:
        """Set whether implicit aspect terms are allowed."""
        self.config["implicit_aspect_term_allowed"] = allowed

    def set_implicit_opinion_allowed(self, allowed: bool) -> None:
        """Set whether implicit opinion terms are allowed."""
        self.config["implicit_opinion_term_allowed"] = allowed

    def set_auto_clean_phrases(self, enabled: bool) -> None:
        """Set whether automatic phrase cleaning is enabled."""
        self.config["auto_clean_phrases"] = enabled

    def set_save_phrase_positions(self, enabled: bool) -> None:
        """Set whether phrase start/end positions are saved (at_start, at_end, ot_start, ot_end)."""
        self.config["save_phrase_positions"] = enabled

    def set_click_on_token(self, enabled: bool) -> None:
        """Set whether click-on-token feature is enabled (snap to token boundaries)."""
        self.config["click_on_token"] = enabled

    def set_auto_positions(self, enabled: bool) -> None:
        """Set whether automatic position data filling is enabled for existing phrases on startup."""
        self.config["auto_positions"] = enabled

    def set_store_time(self, enabled: bool) -> None:
        """Set whether timing data should be stored (duration and change status for each annotation session)."""
        self.config["store_time"] = enabled

    def set_display_avg_annotation_time(self, enabled: bool) -> None:
        """Set whether average annotation time should be displayed."""
        self.config["display_avg_annotation_time"] = enabled

    def set_enable_pre_prediction(self, enabled: bool) -> None:
        """Set whether AI pre-prediction is enabled."""
        self.config["enable_pre_prediction"] = enabled

    def set_disable_ai_automatic_prediction(self, disabled: bool) -> None:
        """Set whether automatic AI prediction triggering is disabled."""
        self.config["disable_ai_automatic_prediction"] = disabled

    def set_annotation_guideline(self, guideline_path: str) -> None:
        """Set the path to the annotation guideline PDF file and encode it as base64."""
        if guideline_path and not os.path.exists(guideline_path):
            raise ValueError(
                f"Annotation guideline file not found: {guideline_path}")

        if guideline_path:
            # Read and encode PDF as base64
            import base64
            with open(guideline_path, 'rb') as pdf_file:
                pdf_data = pdf_file.read()
                encoded_pdf = base64.b64encode(pdf_data).decode('utf-8')
                self.config["annotation_guideline"] = f"data:application/pdf;base64,{encoded_pdf}"
        else:
            self.config["annotation_guideline"] = None

    def set_openai_key(self, openai_key: str) -> None:
        """Set the OpenAI API key for using OpenAI models."""
        self.config["openai_key"] = openai_key

    def set_n_few_shot(self, n_few_shot: int) -> None:
        """Set the maximum number of few-shot examples to include in LLM prompts."""
        if n_few_shot < 0:
            raise ValueError("Number of few-shot examples must be non-negative")
        self.config["n_few_shot"] = n_few_shot

    def set_llm_provider(self, provider: str) -> None:
        """Set the LLM provider (openai, ollama, anthropic, vllm)."""
        valid = ["openai", "ollama", "anthropic", "vllm"]
        provider = provider.lower().strip()
        if provider not in valid:
            raise ValueError(f"Invalid LLM provider: {provider}. Valid options: {valid}")
        self.config["llm_provider"] = provider

    def set_llm_model(self, model: str) -> None:
        """Set the LLM model name."""
        self.config["llm_model"] = model

    def set_anthropic_key(self, anthropic_key: str) -> None:
        """Set the Anthropic API key."""
        self.config["anthropic_key"] = anthropic_key

    def set_vllm_url(self, vllm_url: str) -> None:
        """Set the vLLM server base URL."""
        self.config["vllm_url"] = vllm_url

    def set_vllm_model(self, vllm_model: str) -> None:
        """Set the vLLM model name."""
        self.config["vllm_model"] = vllm_model

    def set_compare_model_a_csv(self, csv_path: str) -> None:
        """Set the CSV path for comparison Model A."""
        self.config["compare_model_a_csv"] = csv_path

    def set_compare_model_a_name(self, name: str) -> None:
        """Set the display name for comparison Model A."""
        self.config["compare_model_a_name"] = name

    def set_compare_model_b_csv(self, csv_path: str) -> None:
        """Set the CSV path for comparison Model B."""
        self.config["compare_model_b_csv"] = csv_path

    def set_compare_model_b_name(self, name: str) -> None:
        """Set the display name for comparison Model B."""
        self.config["compare_model_b_name"] = name

    def set_session_id(self, session_id: str) -> None:
        """Set the session ID for this annotation session."""
        self.config["session_id"] = session_id

    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration."""
        return self.config.copy()

    def save_config(self, output_path: str = "absa_config.json") -> None:
        """Save configuration to JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        print(f"✅ Configuration saved to {output_path}")

    def load_config(self, config_path: str) -> None:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)

            # Update configuration with loaded values
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
        except Exception as e:
            print(f"❌ Error loading configuration: {e}")
            sys.exit(1)

    def print_config(self) -> None:
        """Print the current configuration in a formatted way."""
        print("🎯 ABSA Annotator Configuration")
        print("=" * 40)
        print(f"📄 Data Path: {self.config['csv_path']}")
        if self.config.get('session_id'):
            print(f"🔖 Session ID: {self.config['session_id']}")
        print(
            f"🏷️  Sentiment Elements: {', '.join(self.config['sentiment_elements'])}")
        print(
            f"😊 Sentiment Polarities: {', '.join(self.config['sentiment_polarity_options'])}")
        print(
            f"📝 Aspect Categories: {len(self.config['aspect_categories'])} categories")
        print(
            f"🔍 Implicit Aspect terms: {'✅' if self.config['implicit_aspect_term_allowed'] else '❌'}")
        print(
            f"💭 Implicit Opinion terms: {'✅' if self.config['implicit_opinion_term_allowed'] else '❌'}")
        print(f"🔧 Auto-add Positions: {'✅' if self.config['auto_positions'] else '❌'}")
        print(f"🎯 Few-shot Examples: {self.config['n_few_shot']}")
        provider = self.config.get('llm_provider', 'ollama')
        model = self.config.get('llm_model', 'gemma3:4b')
        print(f"🤖 LLM Provider: {provider} (model: {model})")
        if provider == 'openai' and self.config.get('openai_key'):
            print(f"   🔑 OpenAI key: configured")
        elif provider == 'anthropic' and self.config.get('anthropic_key'):
            print(f"   🔑 Anthropic key: configured")
        elif provider == 'vllm' and self.config.get('vllm_url'):
            vllm_model = self.config.get('vllm_model') or model
            print(f"   🔗 vLLM URL: {self.config['vllm_url']} (model: {vllm_model})")


def start_backend(port: int = 8000, host: str = "localhost", data_path: str = None, config: ABSAAnnotatorConfig = None):
    """Start the FastAPI backend server."""
    global backend_process
    try:
        # Check if port is already in use
        if is_port_in_use(host, port):
            print(f"⚠️  Port {port} is already in use on {host}")
            print(
                f"💡 Backend might already be running on http://{host}:{port}")
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

        # Wait for process to finish or shutdown signal
        while backend_process.poll() is None and not shutdown_flag.is_set():
            time.sleep(0.1)

        if shutdown_flag.is_set():
            cleanup_backend()

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start backend server: {e}")
        if not shutdown_flag.is_set():
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Backend server stopped by user")
        cleanup_backend()


def start_frontend(port: int = 3000, host: str = "localhost", backend_host: str = "localhost", backend_port: int = 8000):
    """Start the React frontend development server."""
    frontend_path = os.path.join(os.getcwd(), "frontend")
    if not os.path.exists(frontend_path):
        print("❌ Frontend directory not found! Make sure you're in the project root.")
        return False

    try:
        print(f"🌐 Starting frontend development server on {host}:{port}...")
        os.chdir(frontend_path)

        # Set environment variables for Vite
        env = os.environ.copy()
        env["VITE_BACKEND_URL"] = f"http://{backend_host}:{backend_port}"

        # Update vite.config.js to use the specified port
        update_vite_port_config(port, host)

        subprocess.run(["npm", "run", "dev"], check=True, env=env)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start frontend server: {e}")
        return False
    except KeyboardInterrupt:
        print("\n🛑 Frontend server stopped by user")
        return True
    except FileNotFoundError:
        print("❌ npm not found! Please install Node.js and npm.")
        return False


def start_full_app(backend_port: int = 8000, backend_host: str = "localhost", frontend_port: int = 3000, frontend_host: str = "localhost", data_path: str = None, config: ABSAAnnotatorConfig = None):
    """Start both backend and frontend servers."""
    print("🚀 Starting AnnoABSA...")
    print("=" * 50)

    # Start backend in a separate thread
    backend_thread = threading.Thread(target=start_backend, args=(
        backend_port, backend_host, data_path, config))
    backend_thread.daemon = False  # Don't make it daemon so we can properly clean up
    backend_thread.start()

    # Wait a moment for backend to start
    print("⏳ Waiting for backend to initialize...")
    time.sleep(3)

    # Start frontend (this will block until stopped)
    try:
        start_frontend(frontend_port, frontend_host,
                       backend_host, backend_port)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down AnnoABSA...")
        shutdown_flag.set()
        cleanup_backend()
        # Wait for backend thread to finish
        if backend_thread.is_alive():
            backend_thread.join(timeout=5)

    # Check if shutdown was triggered
    if shutdown_flag.is_set():
        sys.exit(0)


def update_vite_port_config(port: int, host: str):
    """Update vite.config.js with the specified port and host."""
    vite_config_path = "vite.config.js"
    if not os.path.exists(vite_config_path):
        return

    # Read current config
    with open(vite_config_path, 'r') as f:
        content = f.read()

    # Replace the server configuration
    import re
    pattern = r'server:\s*\{[^}]*\}'
    replacement = f'''server: {{
    port: {port},
    host: '{host}',
    open: true
  }}'''

    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
        with open(vite_config_path, 'w') as f:
            f.write(content)


def is_port_in_use(host: str, port: int) -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def std_triplets_to_label(raw_triplet_str: str) -> list:
    """Convert STD format triplet string to internal label list of dicts.

    STD format: Python list-literal string with single quotes, e.g.
    \"[['NULL', 'course general', 'positive']]\"
    Returns: list of dicts with keys aspect_term, aspect_category,
             sentiment_polarity, opinion_term (empty string).
    Empty or unparseable input returns [] and logs a warning.
    """
    if raw_triplet_str is None or str(raw_triplet_str).strip() in ["", "nan", "None", "[]"]:
        return []
    try:
        parsed = ast.literal_eval(str(raw_triplet_str))
        res = []
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, (list, tuple)) and len(item) >= 3:
                    res.append({
                        "aspect_term": str(item[0]) if item[0] else "NULL",
                        "aspect_category": str(item[1]),
                        "sentiment_polarity": str(item[2]).lower(),
                        "opinion_term": ""
                    })
        return res
    except Exception as e:
        print(f"Warning: Could not parse STD triplet string: {e}")
        return []


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="annoabsa",
        description="🎯 AnnoABSA - Configure and run your annotation environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with CSV path
  annoabsa examples/restaurant_reviews.csv
  
  # Load configuration from file
  annoabsa examples/restaurant_reviews.csv --load-config examples/example_config.json
  
  # Start with a session ID
  annoabsa examples/restaurant_reviews.csv --session-id "user123_session1"
  
  # Start only backend server
  annoabsa examples/restaurant_reviews.csv --backend --backend-port 8001
  
  # Configure elements and save to config file with session ID
  annoabsa examples/restaurant_reviews.csv --elements aspect_term sentiment_polarity --session-id "exp_2024" --save-config examples/quick_config.json
  
  # Load config and override some settings
  annoabsa examples/restaurant_reviews.csv --load-config examples/example_config.json --polarities positive negative
        """
    )

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
        choices=["aspect_term", "aspect_category",
                 "sentiment_polarity", "opinion_term"],
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

    parser.add_argument(
        "--disable-implicit-aspect",
        action="store_true",
        help="Disable implicit aspect terms"
    )

    parser.add_argument(
        "--implicit-opinion",
        action="store_true",
        help="Allow implicit opinion terms"
    )

    parser.add_argument(
        "--disable_implicit_opinion",
        action="store_true",
        default=True,
        help="Disable implicit opinion terms (default)"
    )

    parser.add_argument(
        "--disable_clean_phrases",
        action="store_true",
        help="Disable automatic cleaning of punctuation from selected phrases"
    )

    parser.add_argument(
        "--disable-save-positions",
        action="store_true",
        help="Disable saving of phrase start/end positions (at_start, at_end, ot_start, ot_end)"
    )

    parser.add_argument(
        "--disable-click-on-token",
        action="store_true",
        help="Disable click-on-token feature (precise character clicking instead of token snapping)"
    )

    parser.add_argument(
        "--auto-positions",
        action="store_true",
        help="Automatically add missing position data (at_start, at_end, ot_start, ot_end) for existing phrases on server start"
    )

    parser.add_argument(
        "--store-time",
        action="store_true",
        help="Speichere die Dauer und ob sich die Annotation geändert hat (zwischen Öffnen und Speichern) für jeden Index."
    )

    parser.add_argument(
        "--display-avg-annotation-time",
        action="store_true",
        help="Zeige die durchschnittliche Zeit pro Annotation an (in Sekunden)"
    )

    parser.add_argument(
        "--ai-suggestions",
        dest="enable_pre_prediction",
        action="store_true",
        help="Enable AI pre-prediction feature (default: disabled)"
    )

    parser.add_argument(
        "--disable-ai-automatic-prediction",
        dest="disable_ai_automatic_prediction",
        action="store_true",
        help="Disable automatic AI prediction triggering (AI button still works manually)"
    )

    parser.add_argument(
        "--save-config",
        metavar="PATH",
        nargs="?",
        const="absa_config.json",
        help="Save configuration to JSON file (default: absa_config.json)"
    )

    parser.add_argument(
        "--load-config",
        metavar="PATH",
        help="Load configuration from JSON file"
    )

    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Display the current configuration"
    )

    parser.add_argument(
        "--annotation-guidelines",
        metavar="PDF_PATH",
        help="Path to PDF file containing annotation guidelines to display in the UI"
    )

    parser.add_argument(
        "--openai-key",
        metavar="API_KEY",
        help="OpenAI API key for using OpenAI models instead of local LLM"
    )

    parser.add_argument(
        "--compare-model-a-csv",
        metavar="PATH",
        help="CSV file for comparison Model A (per-row or STD format)"
    )

    parser.add_argument(
        "--compare-model-a-name",
        metavar="NAME",
        default="Model A",
        help="Display name for comparison Model A (default: Model A)"
    )

    parser.add_argument(
        "--compare-model-b-csv",
        metavar="PATH",
        help="CSV file for comparison Model B (per-row or STD format)"
    )

    parser.add_argument(
        "--compare-model-b-name",
        metavar="NAME",
        default="Model B",
        help="Display name for comparison Model B (default: Model B)"
    )

    parser.add_argument(
        "--n-few-shot",
        type=int,
        default=10,
        metavar="N",
        help="Maximum number of few-shot examples to include in LLM prompts (default: 10)"
    )

    parser.add_argument(
        "--llm-provider",
        choices=["openai", "ollama", "anthropic", "vllm"],
        help="LLM provider for AI predictions (default: auto-detect from --openai-key presence)"
    )

    parser.add_argument(
        "--llm-model",
        metavar="MODEL",
        default="gemma3:4b",
        help="Language model for AI predictions (e.g., gemma3:4b for Ollama, gpt-4o-2024-08-06 for OpenAI, claude-sonnet-4-20250514 for Anthropic)"
    )

    parser.add_argument(
        "--anthropic-key",
        metavar="API_KEY",
        help="Anthropic API key for using Anthropic models"
    )

    parser.add_argument(
        "--vllm-url",
        metavar="URL",
        help="vLLM server base URL (e.g., http://localhost:8001/v1)"
    )

    parser.add_argument(
        "--vllm-model",
        metavar="MODEL",
        help="Model name for vLLM (default: uses --llm-model value)"
    )

    parser.add_argument(
        "--format",
        choices=["std"],
        help="Input file format. Use 'std' for two-column (review,triplet) STD format CSV"
    )

    parser.add_argument(
        "--export-std",
        metavar="OUTPUT_PATH",
        help="Export annotated data to STD format CSV at the given path, then exit"
    )

    # Server control arguments
    parser.add_argument(
        "--backend",
        action="store_true",
        help="Start only the backend server"
    )

    parser.add_argument(
        "--backend-port",
        type=int,
        default=8000,
        help="Port for the backend server (default: 8000)"
    )

    parser.add_argument(
        "--backend-ip",
        default="localhost",
        help="IP address for the backend server (default: localhost)"
    )

    parser.add_argument(
        "--frontend-port",
        type=int,
        default=3000,
        help="Port for the frontend server (default: 3000)"
    )

    parser.add_argument(
        "--frontend-ip",
        default="localhost",
        help="IP address for the frontend server (default: localhost)"
    )

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

    # Handle --export-std: export to STD format and exit
    if args.export_std:
        try:
            export_df = pd.read_csv(args.data_path, encoding='utf-8')
        except Exception as e:
            print(f"❌ Error reading data file for export: {e}")
            sys.exit(1)

        export_rows = []
        for _, row in export_df.iterrows():
            review_text = row.get("review_text", row.get("text", ""))
            label_str = row.get("label", "[]")
            if pd.isna(label_str) or str(label_str).strip() in ("", "nan"):
                label_str = "[]"
            try:
                annotations = json.loads(str(label_str))
            except (json.JSONDecodeError, TypeError):
                annotations = []

            triplets = []
            for ann in annotations:
                at = ann.get("aspect_term", "NULL")
                ac = ann.get("aspect_category", "")
                sp = ann.get("sentiment_polarity", "").lower()
                triplets.append([at, ac, sp])

            export_rows.append({"review": review_text, "triplet": repr(triplets)})

        export_out = pd.DataFrame(export_rows)
        export_out.to_csv(args.export_std, index=False, encoding='utf-8')
        print(f"✅ Exported to STD format: {args.export_std}")
        sys.exit(0)

    # Handle --format std: convert STD to internal format before proceeding
    if args.format == "std":
        try:
            std_df = pd.read_csv(args.data_path, encoding='utf-8')
        except Exception as e:
            print(f"❌ Error reading STD file: {e}")
            sys.exit(1)

        # Validate columns
        required_cols = {"review", "triplet"}
        if not required_cols.issubset(std_df.columns):
            print(f"❌ Error: STD format CSV must have 'review' and 'triplet' columns. Found: {list(std_df.columns)}")
            sys.exit(1)

        converted_rows = []
        for _, row in std_df.iterrows():
            review_text = row["review"]
            triplet_str = str(row["triplet"]) if pd.notna(row.get("triplet")) else "[]"
            label = std_triplets_to_label(triplet_str)
            converted_rows.append({
                "review_text": review_text,
                "label": json.dumps(label, ensure_ascii=False)
            })

        base, _ = os.path.splitext(args.data_path)
        working_path = f"{base}_annoabsa.csv"
        converted_df = pd.DataFrame(converted_rows)
        converted_df.to_csv(working_path, index=False, encoding='utf-8')
        print(f"✅ Converted STD format -> internal format: {working_path}")

        # Override data_path to point at the working copy
        args.data_path = working_path
        print(f"📂 Using internal format file: {args.data_path}")

    # Initialize configuration
    config = ABSAAnnotatorConfig(args.data_path)

    # Load configuration from file if specified (before applying command line overrides)
    if args.load_config:
        config.load_config(args.load_config)

    # Apply command line arguments (these override loaded config)
    if args.elements:
        config.set_sentiment_elements(args.elements)

    if args.polarities:
        config.set_sentiment_polarities(args.polarities)

    if args.categories:
        config.set_aspect_categories(args.categories)

    if args.disable_implicit_aspect:
        config.set_implicit_aspect_allowed(False)
    elif args.implicit_aspect:
        config.set_implicit_aspect_allowed(True)

    if args.implicit_opinion:
        config.set_implicit_opinion_allowed(True)
    elif args.disable_implicit_opinion:
        config.set_implicit_opinion_allowed(False)

    if args.disable_clean_phrases:
        config.set_auto_clean_phrases(False)

    if args.disable_save_positions:
        config.set_save_phrase_positions(False)

    if args.disable_click_on_token:
        config.set_click_on_token(False)

    if args.auto_positions:
        config.set_auto_positions(True)

    if args.store_time:
        config.set_store_time(True)

    if args.display_avg_annotation_time:
        config.set_display_avg_annotation_time(True)

    if args.enable_pre_prediction:
        config.set_enable_pre_prediction(True)

    if args.disable_ai_automatic_prediction:
        config.set_disable_ai_automatic_prediction(True)

    if args.annotation_guidelines:
        config.set_annotation_guideline(args.annotation_guidelines)

    if args.openai_key:
        config.set_openai_key(args.openai_key)

    if args.n_few_shot:
        config.set_n_few_shot(args.n_few_shot)

    # LLM provider: use explicit flag, or derive from openai_key presence
    if args.llm_provider:
        config.set_llm_provider(args.llm_provider)
    elif args.openai_key:
        config.set_llm_provider("openai")
    else:
        config.set_llm_provider("ollama")

    if args.llm_model:
        config.set_llm_model(args.llm_model)

    if args.anthropic_key:
        config.set_anthropic_key(args.anthropic_key)

    if args.vllm_url:
        config.set_vllm_url(args.vllm_url)

    if args.vllm_model:
        config.set_vllm_model(args.vllm_model)

    # Validate LLM provider has required configuration
    llm_provider = config.get_config().get("llm_provider")
    if llm_provider == "openai" and not config.get_config().get("openai_key"):
        print("❌ Error: LLM provider 'openai' requires --openai-key")
        sys.exit(1)
    if llm_provider == "anthropic" and not config.get_config().get("anthropic_key"):
        print("❌ Error: LLM provider 'anthropic' requires --anthropic-key")
        sys.exit(1)
    if llm_provider == "vllm" and not config.get_config().get("vllm_url"):
        print("❌ Error: LLM provider 'vllm' requires --vllm-url")
        sys.exit(1)

    if args.compare_model_a_csv:
        config.set_compare_model_a_csv(args.compare_model_a_csv)
    if args.compare_model_a_name:
        config.set_compare_model_a_name(args.compare_model_a_name)
    if args.compare_model_b_csv:
        config.set_compare_model_b_csv(args.compare_model_b_csv)
    if args.compare_model_b_name:
        config.set_compare_model_b_name(args.compare_model_b_name)

    # Show configuration if requested
    if args.show_config:
        config.print_config()

    # Save configuration if requested
    if args.save_config:
        config.save_config(args.save_config)

    # Start servers if requested
    backend_port = args.backend_port
    backend_host = args.backend_ip
    frontend_port = args.frontend_port
    frontend_host = args.frontend_ip

    if args.backend:
        start_backend(backend_port, backend_host, args.data_path, config)
    else:
        # Default behavior: start both servers
        start_full_app(backend_port, backend_host, frontend_port,
                       frontend_host, args.data_path, config)


if __name__ == "__main__":
    main()



