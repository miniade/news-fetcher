"""
Tests for the diversity module.
"""

import pytest
from news_fetcher.diversify import DiversitySelector
from news_fetcher.models import Article
from datetime import datetime


class TestDiversify:
    """Test class for the diversity module."""

    def test_diversify_no_items(self):
        """Test diversifying an empty list of items."""
        selector = DiversitySelector()
        diversified = selector.select([], 5)
        assert diversified == []

    def test_diversify_with_items(self, sample_news_items):
        """Test diversifying a list of news items."""
        articles = [
            Article(
                id=item['id'],
                title=item['title'],
                content=item['content'],
                url=item['url'],
                source=item['source'],
                published_at=datetime(2025, 2, 25)
            )
            for item in sample_news_items
        ]

        selector = DiversitySelector()
        diversified = selector.select(articles, 3)
        assert len(diversified) == 3
