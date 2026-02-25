"""
Tests for the CLI module.
"""

import pytest
from news_fetcher.cli import main
from news_fetcher.config import load_config


class TestCLI:
    """Test class for the CLI."""

    def test_cli_help(self):
        """Test that the CLI help is displayed."""
        with pytest.raises(SystemExit) as excinfo:
            main(["--help"])
        assert excinfo.value.code == 0

    def test_cli_config_loading(self):
        """Test that the CLI loads config correctly."""
        config = load_config("config.yaml")
        assert config is not None
