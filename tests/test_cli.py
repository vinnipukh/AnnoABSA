"""Tests for cli/config.py, cli/convert.py, cli/runner.py."""
import json
import os
import socket
import textwrap
from unittest.mock import MagicMock, patch

import pytest


class TestAbsaAnnotatorConfig:
    """Tests for ABSAAnnotatorConfig (cli/config.py)."""

    # ── Fixtures ──

    @pytest.fixture
    def config(self):
        """Return a default ABSAAnnotatorConfig with a dummy csv_path."""
        from cli.config import ABSAAnnotatorConfig
        return ABSAAnnotatorConfig(csv_path="/dummy/data.csv")

    # ── Constructor defaults ──

    def test_initial_config_has_defaults(self, config):
        """Constructor sets expected default keys and values."""
        cfg = config.config
        assert cfg["csv_path"] == "/dummy/data.csv"
        assert cfg["session_id"] is None
        assert cfg["sentiment_elements"] == [
            "aspect_term", "aspect_category", "sentiment_polarity", "opinion_term"
        ]
        assert cfg["sentiment_polarity_options"] == ["positive", "negative", "neutral"]
        assert isinstance(cfg["aspect_categories"], list)
        assert len(cfg["aspect_categories"]) > 0
        assert cfg["implicit_aspect_term_allowed"] is True
        assert cfg["implicit_opinion_term_allowed"] is False
        assert cfg["n_few_shot"] == 10
        assert cfg["llm_provider"] is None
        assert cfg["llm_model"] == "gemma3:4b"

    # ── Sentiment elements ──

    def test_set_sentiment_elements_valid(self, config):
        """set_sentiment_elements accepts valid element names."""
        elements = ["aspect_term", "opinion_term"]
        config.set_sentiment_elements(elements)
        assert config.config["sentiment_elements"] == elements

    def test_set_sentiment_elements_invalid_raises(self, config):
        """set_sentiment_elements raises ValueError for unknown elements."""
        with pytest.raises(ValueError, match="Invalid sentiment element"):
            config.set_sentiment_elements(["not_a_real_element"])

    # ── Sentiment polarities ──

    def test_set_sentiment_polarities(self, config):
        """set_sentiment_polarities overwrites the polarity options."""
        polarities = ["positive", "negative"]
        config.set_sentiment_polarities(polarities)
        assert config.config["sentiment_polarity_options"] == polarities

    # ── Aspect categories ──

    def test_set_aspect_categories(self, config):
        """set_aspect_categories overwrites the category list."""
        cats = ["food quality", "service general"]
        config.set_aspect_categories(cats)
        assert config.config["aspect_categories"] == cats

    # ── Implicit aspect ──

    def test_set_implicit_aspect_allowed(self, config):
        """set_implicit_aspect_allowed toggles the flag."""
        config.set_implicit_aspect_allowed(False)
        assert config.config["implicit_aspect_term_allowed"] is False
        config.set_implicit_aspect_allowed(True)
        assert config.config["implicit_aspect_term_allowed"] is True

    # ── LLM provider ──

    def test_set_llm_provider_valid(self, config):
        """set_llm_provider accepts valid provider names (case-insensitive)."""
        for provider in ["openai", "OLLAMA", "Anthropic", "vllm"]:
            config.set_llm_provider(provider)
            assert config.config["llm_provider"] == provider.lower().strip()

    def test_set_llm_provider_invalid_raises(self, config):
        """set_llm_provider raises ValueError for unknown providers."""
        with pytest.raises(ValueError, match="Invalid LLM provider"):
            config.set_llm_provider("google")

    # ── n_few_shot ──

    def test_set_n_few_shot_negative_raises(self, config):
        """set_n_few_shot raises ValueError when n < 0."""
        with pytest.raises(ValueError, match="non-negative"):
            config.set_n_few_shot(-1)

    def test_set_n_few_shot_valid(self, config):
        """set_n_few_shot accepts non-negative integers."""
        config.set_n_few_shot(5)
        assert config.config["n_few_shot"] == 5
        config.set_n_few_shot(0)
        assert config.config["n_few_shot"] == 0

    # ── Annotation guideline ──

    def test_set_annotation_guideline_missing_raises(self, config):
        """set_annotation_guideline raises ValueError when file not found."""
        with pytest.raises(ValueError, match="not found"):
            config.set_annotation_guideline("/nonexistent/path.pdf")

    def test_set_annotation_guideline_none(self, config):
        """set_annotation_guideline(None) sets the field to None."""
        config.set_annotation_guideline(None)
        assert config.config["annotation_guideline"] is None

    def test_set_annotation_guideline_valid_file(self, config, tmp_path):
        """set_annotation_guideline reads, base64-encodes a PDF and stores a data URI."""
        pdf_path = tmp_path / "guide.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake pdf content")
        config.set_annotation_guideline(str(pdf_path))
        val = config.config["annotation_guideline"]
        assert val.startswith("data:application/pdf;base64,")
        # Verify it's actually base64 of the content
        import base64
        expected_b64 = base64.b64encode(b"%PDF-1.4 fake pdf content").decode("utf-8")
        assert val == f"data:application/pdf;base64,{expected_b64}"

    # ── get_config ──

    def test_get_config_returns_copy(self, config):
        """get_config returns a copy, not the internal dict."""
        returned = config.get_config()
        returned["csv_path"] = "/hacked/path.csv"
        assert config.config["csv_path"] == "/dummy/data.csv"

    # ── save / load roundtrip ──

    def test_save_and_load_roundtrip(self, config, tmp_path):
        """save_config → load_config roundtrips all keys correctly."""
        # Mutate some values
        config.set_sentiment_elements(["aspect_term"])
        config.set_llm_provider("ollama")
        config.config["session_id"] = "test-session-001"

        out_path = str(tmp_path / "absa_config.json")
        config.save_config(out_path)

        # Create a fresh config and load
        from cli.config import ABSAAnnotatorConfig
        fresh = ABSAAnnotatorConfig(csv_path="/other/data.csv")
        fresh.load_config(out_path)

        assert fresh.config["csv_path"] == "/dummy/data.csv"  # from saved config
        assert fresh.config["sentiment_elements"] == ["aspect_term"]
        assert fresh.config["llm_provider"] == "ollama"
        assert fresh.config["session_id"] == "test-session-001"

    def test_save_config_writes_valid_json(self, config, tmp_path):
        """save_config writes well-formed JSON."""
        out_path = str(tmp_path / "absa_config.json")
        config.save_config(out_path)
        with open(out_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["csv_path"] == "/dummy/data.csv"

    # ── load_config error paths ──

    def test_load_config_file_not_found_exits(self, config):
        """load_config with a missing file prints error and calls sys.exit(1)."""
        with pytest.raises(SystemExit) as exc_info:
            config.load_config("/definitely/does/not/exist.json")
        assert exc_info.value.code == 1

    def test_load_config_invalid_json_exits(self, config, tmp_path):
        """load_config with malformed JSON prints error and calls sys.exit(1)."""
        bad_path = str(tmp_path / "bad.json")
        with open(bad_path, "w", encoding="utf-8") as f:
            f.write("{not valid json")
        with pytest.raises(SystemExit) as exc_info:
            config.load_config(bad_path)
        assert exc_info.value.code == 1


class TestStdTripletsToLabel:
    """Tests for std_triplets_to_label (cli/convert.py)."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from cli.convert import std_triplets_to_label
        self.convert = std_triplets_to_label

    def test_valid_triplet_string(self):
        """A valid triplet string is parsed into a list of dicts."""
        result = self.convert("[['NULL', 'food quality', 'positive']]")
        assert len(result) == 1
        entry = result[0]
        assert entry["aspect_term"] == "NULL"
        assert entry["aspect_category"] == "food quality"
        assert entry["sentiment_polarity"] == "positive"
        assert entry["opinion_term"] == ""

    def test_empty_string_returns_empty(self):
        """Empty string returns empty list."""
        assert self.convert("") == []

    def test_nan_string_returns_empty(self):
        """'nan' string returns empty list."""
        assert self.convert("nan") == []

    def test_none_returns_empty(self):
        """None input returns empty list."""
        assert self.convert(None) == []

    def test_multi_triplet_parsing(self):
        """Multiple triplets in one string are all parsed."""
        raw = (
            "[['NULL', 'food quality', 'positive'], "
            "['the steak', 'food general', 'negative']]"
        )
        result = self.convert(raw)
        assert len(result) == 2
        assert result[0]["aspect_term"] == "NULL"
        assert result[1]["aspect_term"] == "the steak"
        assert result[1]["aspect_category"] == "food general"
        assert result[1]["sentiment_polarity"] == "negative"

    def test_short_triplet_skipped(self):
        """Triplets with fewer than 3 items are silently skipped."""
        raw = "[['too', 'short'], ['valid', 'food quality', 'positive']]"
        result = self.convert(raw)
        assert len(result) == 1
        assert result[0]["aspect_category"] == "food quality"

    def test_invalid_input_returns_empty(self):
        """Unparseable / malformed input returns empty list without crashing."""
        assert self.convert("{{{not a list}}}") == []
        assert self.convert("[broken") == []


class TestRunnerUtils:
    """Tests for utility functions in cli/runner.py."""

    # ── is_port_in_use ──

    def test_is_port_in_use_free_port(self):
        """Returns False when socket.bind succeeds (port is free)."""
        from cli.runner import is_port_in_use

        with patch("cli.runner.socket.socket") as mock_sock_cls:
            mock_sock = MagicMock()
            mock_sock_cls.return_value.__enter__.return_value = mock_sock
            # bind succeeds → port is free
            result = is_port_in_use("localhost", 9999)
        assert result is False

    def test_is_port_in_use_bound_port(self):
        """Returns True when socket.bind raises OSError (port is in use)."""
        from cli.runner import is_port_in_use

        with patch("cli.runner.socket.socket") as mock_sock_cls:
            mock_sock = MagicMock()
            mock_sock_cls.return_value.__enter__.return_value = mock_sock
            mock_sock.bind.side_effect = OSError("Address already in use")
            result = is_port_in_use("localhost", 9999)
        assert result is True

    def test_is_port_in_use_calls_bind(self):
        """is_port_in_use calls socket.bind with the correct host and port."""
        from cli.runner import is_port_in_use

        with patch("cli.runner.socket.socket") as mock_sock_cls:
            mock_sock = MagicMock()
            mock_sock_cls.return_value.__enter__.return_value = mock_sock
            is_port_in_use("127.0.0.1", 8080)
        mock_sock.bind.assert_called_once_with(("127.0.0.1", 8080))

    # ── update_vite_port_config ──

    def test_update_vite_port_config(self, tmp_path):
        """update_vite_port_config rewrites the server block in vite.config.js."""
        from cli.runner import update_vite_port_config

        # Create a mock vite.config.js
        original = textwrap.dedent("""\
            import { defineConfig } from 'vite'
            export default defineConfig({
              server: {
                port: 3000,
                host: 'localhost',
                open: true
              }
            })
        """)
        config_path = tmp_path / "vite.config.js"
        config_path.write_text(original)

        # Save original cwd and cd into tmp_path
        orig_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            update_vite_port_config(4000, "0.0.0.0")
        finally:
            os.chdir(orig_cwd)

        updated = config_path.read_text()
        assert "port: 4000" in updated
        assert "host: '0.0.0.0'" in updated
        # Original values should be gone
        assert "port: 3000" not in updated
        assert "host: 'localhost'" not in updated

    def test_update_vite_port_config_no_file(self, tmp_path):
        """update_vite_port_config silently does nothing when vite.config.js doesn't exist."""
        from cli.runner import update_vite_port_config

        orig_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            # Should not raise
            update_vite_port_config(4000, "0.0.0.0")
        finally:
            os.chdir(orig_cwd)

    def test_update_vite_port_config_no_server_block(self, tmp_path):
        """update_vite_port_config leaves files without a server block unchanged."""
        from cli.runner import update_vite_port_config

        no_server = textwrap.dedent("""\
            import { defineConfig } from 'vite'
            export default defineConfig({
              plugins: [vue()]
            })
        """)
        config_path = tmp_path / "vite.config.js"
        config_path.write_text(no_server)

        orig_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))
            update_vite_port_config(4000, "0.0.0.0")
        finally:
            os.chdir(orig_cwd)

        assert config_path.read_text() == no_server
