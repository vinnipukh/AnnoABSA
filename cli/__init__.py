"""AnnoABSA CLI package — split from the monolithic cli.py."""

from cli.config import ABSAAnnotatorConfig
from cli.runner import start_backend, start_frontend, start_full_app
from cli.convert import std_triplets_to_label

import argparse
import json
import sys
import os
import pandas as pd


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
        "--model-a-provider",
        choices=["openai", "ollama", "anthropic", "vllm", "custom_openai"],
        help="Provider for Model A in Live Compare mode"
    )
    parser.add_argument(
        "--model-a-model",
        metavar="MODEL",
        help="Model name for Model A in Live Compare mode"
    )
    parser.add_argument(
        "--model-a-temperature",
        type=float,
        default=0.7,
        help="Temperature for Model A (default: 0.7)"
    )
    parser.add_argument(
        "--model-a-prompt",
        metavar="TEMPLATE",
        help="Prompt template for Model A in Live Compare mode"
    )
    parser.add_argument(
        "--model-b-provider",
        choices=["openai", "ollama", "anthropic", "vllm", "custom_openai"],
        help="Provider for Model B in Live Compare mode"
    )
    parser.add_argument(
        "--model-b-model",
        metavar="MODEL",
        help="Model name for Model B in Live Compare mode"
    )
    parser.add_argument(
        "--model-b-temperature",
        type=float,
        default=0.7,
        help="Temperature for Model B (default: 0.7)"
    )
    parser.add_argument(
        "--model-b-prompt",
        metavar="TEMPLATE",
        help="Prompt template for Model B in Live Compare mode"
    )
    parser.add_argument(
        "--helper-agent-provider",
        choices=["openai", "ollama", "anthropic", "vllm", "custom_openai"],
        help="Provider for Helper Agent in Live Compare mode"
    )
    parser.add_argument(
        "--helper-agent-model",
        metavar="MODEL",
        help="Model name for Helper Agent in Live Compare mode"
    )
    parser.add_argument(
        "--helper-agent-temperature",
        type=float,
        default=0.7,
        help="Temperature for Helper Agent (default: 0.7)"
    )
    parser.add_argument(
        "--helper-agent-prompt",
        metavar="TEMPLATE",
        help="Prompt template for Helper Agent in Live Compare mode"
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

    # LLM provider: use explicit flag, or derive from configured keys
    from services.llm_providers import _derive_provider, validate_provider_config
    provider_config = {
        "llm_provider": args.llm_provider,
        "openai_key": args.openai_key,
        "anthropic_key": args.anthropic_key,
        "vllm_url": args.vllm_url,
    }
    try:
        derived = _derive_provider(provider_config)
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    config.set_llm_provider(derived)

    if args.llm_model:
        config.set_llm_model(args.llm_model)

    if args.anthropic_key:
        config.set_anthropic_key(args.anthropic_key)

    if args.vllm_url:
        config.set_vllm_url(args.vllm_url)

    if args.vllm_model:
        config.set_vllm_model(args.vllm_model)

    if args.model_a_provider:
        config.config["model_a_provider"] = args.model_a_provider
    if args.model_a_model:
        config.config["model_a_model"] = args.model_a_model
    if args.model_a_temperature != 0.7:
        config.config["model_a_temperature"] = args.model_a_temperature
    if args.model_a_prompt:
        config.config["model_a_prompt"] = args.model_a_prompt

    if args.model_b_provider:
        config.config["model_b_provider"] = args.model_b_provider
    if args.model_b_model:
        config.config["model_b_model"] = args.model_b_model
    if args.model_b_temperature != 0.7:
        config.config["model_b_temperature"] = args.model_b_temperature
    if args.model_b_prompt:
        config.config["model_b_prompt"] = args.model_b_prompt

    if args.helper_agent_provider:
        config.config["helper_agent_provider"] = args.helper_agent_provider
    if args.helper_agent_model:
        config.config["helper_agent_model"] = args.helper_agent_model
    if args.helper_agent_temperature != 0.7:
        config.config["helper_agent_temperature"] = args.helper_agent_temperature
    if args.helper_agent_prompt:
        config.config["helper_agent_prompt"] = args.helper_agent_prompt

    # Validate LLM provider has required configuration
    errors = validate_provider_config(derived, config.get_config())
    if errors:
        for err in errors:
            print(f"❌ Error: {err}")
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
