"""
Tests for the normalize module.
"""

import pytest
from news_fetcher.normalize import normalize_text, normalize_title, normalize_url, extract_published_date, dedupe_articles
from news_fetcher.models import Article
from datetime import datetime


class TestNormalize:
    """Test class for the normalize module."""

    def test_normalize_text(self):
        """Test text normalization."""
        text = "  This is a  test  text.  \n\nWith  multiple   spaces.\n"
        normalized = normalize_text(text)
        assert normalized == "This is a test text. With multiple spaces."

    def test_normalize_title(self):
        """Test title normalization."""
        title = "  Test Article Title!  "
        normalized = normalize_title(title)
        assert normalized == "Test Article Title!"

    def test_normalize_url(self):
        """Test URL normalization."""
        url1 = "HTTP://EXAMPLE.COM/ARTICLE?param=1&param=2"
        url2 = "article.html"
        normalized1 = normalize_url(url1)
        normalized2 = normalize_url(url2)
        assert normalized1 == "http://example.com/article?param=1&param=2"
        assert normalized2 == "http://article.html"

    def test_extract_published_date(self):
        """Test published date extraction."""
        entry_with_date = {'published_parsed': (2025, 2, 25, 10, 30, 0)}
        entry_without_date = {}
        date1 = extract_published_date(entry_with_date)
        date2 = extract_published_date(entry_without_date)
        assert isinstance(date1, datetime)
        assert isinstance(date2, datetime)
        assert date1.year == 2025

    def test_dedupe_articles(self):
        """Test deduplication of articles."""
        article1 = Article(
            id="1",
            title="Test Article",
            content="Test content",
            url="https://example.com/article",
            source="example",
            published_at=datetime(2025, 2, 25)
        )

        article2 = Article(
            id="2",
            title="Test Article",
            content="Test content",
            url="https://example.com/article",
            source="example",
            published_at=datetime(2025, 2, 25)
        )

        deduplicated = dedupe_articles([article1, article2])
        assert len(deduplicated) == 1
