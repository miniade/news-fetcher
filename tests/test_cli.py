"""
Tests for the CLI module.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.cli import main


class TestCLI:
    """Test class for CLI functionality."""

    @patch('src.cli.argparse.ArgumentParser.parse_args')
    @patch('src.cli.run_pipeline')
    def test_cli_with_default_args(self, mock_run, mock_parse):
        """Test CLI with default arguments."""
        # Arrange
        mock_parse.return_value = MagicMock(
            config='config.yaml',
            output=None,
            verbose=False
        )

        # Act
        main()

        # Assert
        mock_run.assert_called_once()

    @patch('src.cli.argparse.ArgumentParser.parse_args')
    @patch('src.cli.run_pipeline')
    def test_cli_with_custom_output(self, mock_run, mock_parse):
        """Test CLI with custom output directory."""
        # Arrange
        mock_parse.return_value = MagicMock(
            config='config.yaml',
            output='custom_output',
            verbose=True
        )

        # Act
        main()

        # Assert
        mock_run.assert_called_once()

    @patch('src.cli.argparse.ArgumentParser.parse_args')
    @patch('src.cli.run_pipeline')
    def test_cli_with_verbose_mode(self, mock_run, mock_parse):
        """Test CLI with verbose output mode."""
        # Arrange
        mock_parse.return_value = MagicMock(
            config='config.yaml',
            output=None,
            verbose=True
        )

        # Act
        main()

        # Assert
        mock_run.assert_called_once()

    @patch('src.cli.argparse.ArgumentParser.parse_args')
    def test_cli_with_invalid_config(self, mock_parse):
        """Test CLI with invalid configuration file."""
        # Arrange
        mock_parse.return_value = MagicMock(
            config='nonexistent_config.yaml',
            output=None,
            verbose=False
        )

        # Act & Assert
        with pytest.raises(SystemExit):
            main()