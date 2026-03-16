"""Tests for the rank module."""

from datetime import datetime, timedelta

from news_fetcher.models import Article, Cluster, Config, Source
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

    def test_rank_uses_acquisition_metadata_and_corroboration_to_raise_event(self):
        config = Config(
            sources=[
                Source(name="Official Blog", url="https://official.example", weight=1.0),
                Source(name="Independent Wire", url="https://wire.example", weight=1.0),
                Source(name="Fast Feed", url="https://fast.example", weight=1.0),
            ],
            thresholds={
                "similarity": 0.8,
                "min_score": 0.0,
                "cluster_size": 1,
                "max_per_source": 0,
                "corroboration_min_sources": 2,
            },
        )
        ranker = ArticleRanker(config)
        now = datetime.now()

        official_frontpage = Article(
            id="official-frontpage",
            title="Company confirms launch date",
            content="Detailed launch coverage",
            url="https://official.example/launch",
            source="Official Blog",
            published_at=now - timedelta(hours=3),
            score=5.0,
            cluster_id="launch-event",
            source_official_flag=True,
            source_rank_position=1,
            acquisition_confidence=0.9,
        )
        corroborating_report = Article(
            id="wire-match",
            title="Independent report confirms launch date",
            content="Independent corroboration",
            url="https://wire.example/launch",
            source="Independent Wire",
            published_at=now - timedelta(hours=4),
            score=4.0,
            cluster_id="launch-event",
        )
        fresher_single_source = Article(
            id="fresh-single-source",
            title="Fresh single-source rumor",
            content="Rumor coverage only",
            url="https://fast.example/rumor",
            source="Fast Feed",
            published_at=now,
            score=6.0,
            cluster_id="rumor-event",
        )

        ranked = ranker.rank(
            [fresher_single_source, official_frontpage, corroborating_report],
            clusters=[
                Cluster(id="launch-event", articles=[official_frontpage, corroborating_report]),
                Cluster(id="rumor-event", articles=[fresher_single_source]),
            ],
        )

        assert [article.id for article in ranked] == [
            "official-frontpage",
            "fresh-single-source",
            "wire-match",
        ]

    def test_rank_uses_engagement_proxy_when_available(self):
        config = Config(
            sources=[Source(name="Community", url="https://community.example", weight=1.0)]
        )
        ranker = ArticleRanker(config)
        now = datetime.now()
        articles = [
            Article(
                id="high-engagement",
                title="High engagement",
                content="same content",
                url="https://community.example/high",
                source="Community",
                published_at=now,
                source_rank_position=5,
                source_comment_count=120,
                source_like_count=80,
                score=5.0,
            ),
            Article(
                id="low-engagement",
                title="Low engagement",
                content="same content",
                url="https://community.example/low",
                source="Community",
                published_at=now,
                source_rank_position=5,
                source_comment_count=2,
                source_like_count=1,
                score=5.0,
            ),
        ]

        ranked = ranker.rank(articles)

        assert ranked[0].id == "high-engagement"
