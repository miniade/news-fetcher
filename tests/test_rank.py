"""
Tests for the rank module.
"""

import pytest
from news_fetcher.rank import ArticleRanker
from news_fetcher.models import Article
from news_fetcher.models import Config, Source
from datetime import datetime


class TestRank:
    """Test class for the rank module."""

    def test_rank_no_items(self):
        """Test ranking an empty list of items."""
        config = Config(sources=[])
        ranker = ArticleRanker(config)
        ranked = ranker.rank([])
        assert ranked == []

    def test_rank_with_items(self, sample_news_items):
        """Test ranking a list of news items."""
        config = Config(sources=[
            Source(name="Example", url="https://example.com", weight=1.0),
            Source(name="Financial Times", url="https://ft.com", weight=1.5),
            Source(name="Environmental News", url="https://en.com", weight=1.2)
        ])
        ranker = ArticleRanker(config)
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

        ranked = ranker.rank(articles)
        assert len(ranked) == 3
