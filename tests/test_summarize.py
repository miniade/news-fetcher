"""
Tests for the summarize module - summarizing news content.
"""

import pytest
from src.summarize import summarize_news_items


class TestSummarize:
    """Test class for summarization module functionality."""

    def test_summarize_valid_content(self, sample_news_items):
        """Test summarization of valid news content."""
        # Act
        summarized = summarize_news_items(sample_news_items)

        # Assert
        assert len(summarized) == len(sample_news_items)
        assert all("summary" in item for item in summarized)
        assert all(len(item["summary"]) > 0 for item in summarized)

    def test_summarize_short_content(self):
        """Test summarization of very short content."""
        # Arrange
        short_items = [
            {
                "id": "1",
                "title": "Short News",
                "content": "This is very short content."
            }
        ]

        # Act
        summarized = summarize_news_items(short_items)

        # Assert
        assert len(summarized) == 1
        assert summarized[0]["summary"] == short_items[0]["content"]

    def test_summarize_empty_content(self):
        """Test summarization of empty content."""
        # Arrange
        empty_items = [
            {
                "id": "1",
                "title": "Empty Content",
                "content": ""
            }
        ]

        # Act
        summarized = summarize_news_items(empty_items)

        # Assert
        assert len(summarized) == 1
        assert summarized[0]["summary"] == ""