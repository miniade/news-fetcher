"""
Tests for the output module.
"""

import pytest
from news_fetcher.output import OutputFormatter
from news_fetcher.models import Article
from datetime import datetime
import os
import json


class TestOutput:
    """Test class for the output module."""

    def test_format_json(self):
        """Test that JSON format works."""
        formatter = OutputFormatter(output_format="json")
        articles = [
            Article(
                id="1",
                title="Test Article 1",
                content="Test content 1",
                url="https://example.com/news1",
                source="Example News",
                published_at=datetime(2025, 2, 25),
                fetched_at=datetime(2025, 2, 25)
            )
        ]
        output = formatter.format(articles)
        assert "Test Article 1" in output

    def test_format_markdown(self):
        """Test that Markdown format works."""
        formatter = OutputFormatter(output_format="markdown")
        articles = [
            Article(
                id="1",
                title="Test Article 1",
                content="Test content 1",
                url="https://example.com/news1",
                source="Example News",
                published_at=datetime(2025, 2, 25),
                fetched_at=datetime(2025, 2, 25)
            )
        ]
        output = formatter.format(articles)
        assert "Test Article 1" in output

    def test_format_csv(self):
        """Test that CSV format works."""
        formatter = OutputFormatter(output_format="csv")
        articles = [
            Article(
                id="1",
                title="Test Article 1",
                content="Test content 1",
                url="https://example.com/news1",
                source="Example News",
                published_at=datetime(2025, 2, 25),
                fetched_at=datetime(2025, 2, 25)
            )
        ]
        output = formatter.format(articles)
        assert "Test Article 1" in output

    def test_format_rss(self):
        """Test that RSS format works."""
        formatter = OutputFormatter(output_format="rss")
        articles = [
            Article(
                id="1",
                title="Test Article 1",
                content="Test content 1",
                url="https://example.com/news1",
                source="Example News",
                published_at=datetime(2025, 2, 25),
                fetched_at=datetime(2025, 2, 25)
            )
        ]
        output = formatter.format(articles)
        assert "Test Article 1" in output
