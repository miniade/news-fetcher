"""
Tests for the summarize module.
"""

import pytest
from news_fetcher.summarize import ArticleSummarizer
from news_fetcher.models import Article
from datetime import datetime


class TestSummarize:
    """Test class for the summarize module."""

    def test_summarize_no_items(self):
        """Test summarizing an empty list of items."""
        summarizer = ArticleSummarizer()
        summary = summarizer.summarize_text("")
        assert summary == ""

    def test_summarize_with_items(self, sample_news_items):
        """Test summarizing a list of news items."""
        summarizer = ArticleSummarizer()
        for item in sample_news_items:
            article = Article(
                id=item['id'],
                title=item['title'],
                content=item['content'],
                url=item['url'],
                source=item['source'],
                published_at=datetime(2025, 2, 25)
            )
            summary = summarizer.summarize(article)
            assert len(summary) > 0
