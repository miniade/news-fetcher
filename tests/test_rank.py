"""Tests for the rank module."""

from datetime import datetime, timedelta

from news_fetcher.models import Article, Config, Source
from news_fetcher.rank import ArticleRanker


class TestRank:
    """Test class for the rank module."""

    def test_rank_no_items(self):
        config = Config(sources=[])
        ranker = ArticleRanker(config)
        ranked = ranker.rank([])
        assert ranked == []

    def test_rank_with_items(self, sample_news_items):
        config = Config(
            sources=[
                Source(name="Example", url="https://example.com", weight=1.0),
                Source(name="Financial Times", url="https://ft.com", weight=1.5),
                Source(name="Environmental News", url="https://en.com", weight=1.2),
            ]
        )
        ranker = ArticleRanker(config)
        articles = [
            Article(
                id=item["id"],
                title=item["title"],
                content=item["content"],
                url=item["url"],
                source=item["source"],
                published_at=datetime(2025, 2, 25),
            )
            for item in sample_news_items
        ]

        ranked = ranker.rank(articles)
        assert len(ranked) == 3

    def test_rank_uses_configured_source_weight(self):
        config = Config(
            sources=[
                Source(name="High Weight", url="https://high.example", weight=1.5),
                Source(name="Low Weight", url="https://low.example", weight=0.8),
            ]
        )
        ranker = ArticleRanker(config)
        now = datetime.now()
        articles = [
            Article(
                id="high",
                title="High",
                content="same content",
                url="https://high.example/1",
                source="High Weight",
                published_at=now,
            ),
            Article(
                id="low",
                title="Low",
                content="same content",
                url="https://low.example/1",
                source="Low Weight",
                published_at=now,
            ),
        ]

        ranked = ranker.rank(articles)
        assert ranked[0].id == "high"

    def test_rank_prefers_newer_articles(self):
        config = Config(sources=[Source(name="Example", url="https://example.com", weight=1.0)])
        ranker = ArticleRanker(config)
        now = datetime.now()
        articles = [
            Article(
                id="new",
                title="New",
                content="same content",
                url="https://example.com/new",
                source="Example",
                published_at=now,
            ),
            Article(
                id="old",
                title="Old",
                content="same content",
                url="https://example.com/old",
                source="Example",
                published_at=now - timedelta(days=2),
            ),
        ]

        ranked = ranker.rank(articles)
        assert ranked[0].id == "new"
