"""Tests for the diversity module."""

from datetime import datetime

from news_fetcher.diversify import DiversitySelector, round_robin_select
from news_fetcher.models import Article


class TestDiversify:
    """Test class for the diversity module."""

    def test_diversify_no_items(self):
        selector = DiversitySelector()
        diversified = selector.select([], 5)
        assert diversified == []

    def test_diversify_with_items(self, sample_news_items):
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

        selector = DiversitySelector()
        diversified = selector.select(articles, 3)
        assert len(diversified) == 3

    def test_diversify_balances_sources_with_cap(self):
        now = datetime(2026, 3, 12)
        articles = [
            Article(
                id=f"tc-{i}",
                title=f"TC {i}",
                content="TechCrunch article",
                url=f"https://example.com/tc-{i}",
                source="TechCrunch",
                published_at=now,
                score=1.0 - i * 0.01,
            )
            for i in range(4)
        ] + [
            Article(
                id=f"bbc-{i}",
                title=f"BBC {i}",
                content="BBC article",
                url=f"https://example.com/bbc-{i}",
                source="BBC News",
                published_at=now,
                score=0.9 - i * 0.01,
            )
            for i in range(4)
        ]

        selector = DiversitySelector()
        diversified = selector.select(articles, 4, max_per_source=2)

        assert [article.source for article in diversified] == [
            "TechCrunch",
            "BBC News",
            "TechCrunch",
            "BBC News",
        ]

    def test_diversify_honors_per_source_limits_without_global_cap(self):
        now = datetime(2026, 3, 12)
        articles = [
            Article(
                id=f"weak-{i}",
                title=f"Weak {i}",
                content="Weak article",
                url=f"https://example.com/weak-{i}",
                source="Weak Feed",
                published_at=now,
                score=1.0 - i * 0.01,
            )
            for i in range(3)
        ] + [
            Article(
                id=f"strong-{i}",
                title=f"Strong {i}",
                content="Strong article",
                url=f"https://example.com/strong-{i}",
                source="Strong Feed",
                published_at=now,
                score=0.9 - i * 0.01,
            )
            for i in range(3)
        ]

        selector = DiversitySelector()
        diversified = selector.select(
            articles,
            4,
            per_source_limits={"Weak Feed": 1},
        )

        assert [article.source for article in diversified] == [
            "Weak Feed",
            "Strong Feed",
            "Strong Feed",
            "Strong Feed",
        ]

    def test_round_robin_allows_unlimited_default_when_only_overrides_are_provided(self):
        now = datetime(2026, 3, 12)
        articles = [
            Article(
                id=f"weak-{i}",
                title=f"Weak {i}",
                content="Weak article",
                url=f"https://example.com/weak-{i}",
                source="Weak Feed",
                published_at=now,
                score=1.0 - i * 0.01,
            )
            for i in range(3)
        ] + [
            Article(
                id=f"strong-{i}",
                title=f"Strong {i}",
                content="Strong article",
                url=f"https://example.com/strong-{i}",
                source="Strong Feed",
                published_at=now,
                score=0.9 - i * 0.01,
            )
            for i in range(3)
        ]

        diversified = round_robin_select(
            candidates=articles,
            selected=[],
            k=4,
            max_per_source=None,
            per_source_limits={"Weak Feed": 1},
        )

        assert [article.source for article in diversified] == [
            "Weak Feed",
            "Strong Feed",
            "Strong Feed",
            "Strong Feed",
        ]
