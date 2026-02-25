"""
Tests for the output module - saving results in various formats.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from src.output import save_json, save_rss, generate_output_directory


class TestOutput:
    """Test class for output module functionality."""

    @patch('src.output.os.makedirs')
    @patch('src.output.open', new_callable=MagicMock)
    def test_save_json_output(self, mock_open, mock_makedirs, sample_news_items):
        """Test saving news items in JSON format."""
        # Act
        save_json(sample_news_items, "test_output")

        # Assert
        mock_makedirs.assert_called_once()
        mock_open.assert_called_once()

    @patch('src.output.os.makedirs')
    @patch('src.output.open', new_callable=MagicMock)
    def test_save_rss_output(self, mock_open, mock_makedirs, sample_news_items):
        """Test saving news items in RSS format."""
        # Act
        save_rss(sample_news_items, "test_output")

        # Assert
        mock_makedirs.assert_called_once()
        mock_open.assert_called_once()

    def test_generate_output_directory(self):
        """Test output directory generation."""
        # Act
        directory = generate_output_directory()

        # Assert
        assert isinstance(directory, str)
        assert len(directory) > 0

    @patch('src.output.os.makedirs')
    def test_create_output_directory(self, mock_makedirs):
        """Test directory creation if it doesn't exist."""
        # Arrange
        mock_makedirs.side_effect = None

        # Act
        with patch('src.output.os.path.exists', return_value=False):
            generate_output_directory("custom_output")

        # Assert
        mock_makedirs.assert_called_once()