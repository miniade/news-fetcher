"""
End-to-end tests for the news-fetcher application.
"""

import pytest
from news_fetcher.cli import main


class TestE2E:
    """Test class for end-to-end testing."""

    def test_e2e_help(self):
        """Test that the main function helps."""
        with pytest.raises(SystemExit) as excinfo:
            main(["--help"])
        assert excinfo.value.code == 0

    def test_e2e_run_command(self):
        """Test that the run command is available."""
        with pytest.raises(SystemExit) as excinfo:
            main(["run", "--help"])
        assert excinfo.value.code == 0
