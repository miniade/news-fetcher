"""Tests for the main pipeline."""

from datetime import datetime, timedelta, timezone

import responses

import news_fetcher.pipeline as pipeline_module
from news_fetcher.models import Article, Cluster, Config, Source
from news_fetcher.pipeline import NewsPipeline


class TestPipeline:
    def test_pipeline_applies_min_score_and_prunes_clusters(self, monkeypatch):
        config = Config(
            sources=[Source(name="Example", url="https://example.com/feed.xml")],
            thresholds={
                "similarity": 0.8,
                "min_score": 0.3,
                "cluster_size": 1,
                "max_per_source": 0,
            },
        )
        pipeline = NewsPipeline(config)

        article_kept = Article(
            id="keep",
            title="Keep me",
            content="content",
            url="https://example.com/keep",
            source="Example",
            published_at=datetime(2026, 3, 12),
            score=0.35,
        )
        article_dropped = Article(
            id="drop",
            title="Drop me",
            content="content",
            url="https://example.com/drop",
            source="Example",
            published_at=datetime(2026, 3, 12),
            score=0.2,
        )
        cluster = Cluster(
            id="cluster-1",
            articles=[article_kept, article_dropped],
            representative_article=article_dropped,
        )

        monkeypatch.setattr(pipeline, "_fetch", lambda sources, since: [article_kept, article_dropped])
        monkeypatch.setattr(pipeline, "_normalize", lambda articles: articles)
        monkeypatch.setattr(pipeline, "_deduplicate", lambda articles: articles)
        monkeypatch.setattr(pipeline, "_cluster", lambda articles: (articles, [cluster]))
        monkeypatch.setattr(
            pipeline,
            "_rank",
            lambda articles, clusters: [article_kept, article_dropped],
        )
        monkeypatch.setattr(pipeline, "_diversify", lambda articles, limit=None: articles)
        monkeypatch.setattr(pipeline, "_summarize", lambda articles: articles)

        result = pipeline.run(limit=10)

        assert [article.id for article in result.articles] == ["keep"]
        assert len(result.clusters) == 1
        assert [article.id for article in result.clusters[0].articles] == ["keep"]
        assert result.clusters[0].representative_article.id == "keep"

    def test_pipeline_preserves_acquisition_metadata_through_fetch_and_normalize(
        self, monkeypatch, mock_http_responses
    ):
        test_url = "https://example.com/frontpage"
        html = """
<html>
  <body>
    <main>
      <div class="lead-story">
        <h2><a href="/story-1">Lead Story Headline</a></h2>
        <p>Lead summary.</p>
      </div>
    </main>
  </body>
</html>
"""
        mock_http_responses.add(
            responses.GET,
            test_url,
            body=html,
            status=200,
            content_type="text/html",
        )
        config = Config(
            sources=[
                Source(
                    name="Frontpage Source",
                    url=test_url,
                    type="html",
                    selector=".lead-story",
                    source_type="publisher_section",
                    candidate_strategy="section_frontpage",
                )
            ],
            thresholds={
                "similarity": 0.8,
                "min_score": 0.0,
                "cluster_size": 1,
                "max_per_source": 0,
            },
        )
        pipeline = NewsPipeline(config)

        monkeypatch.setattr(pipeline, "_deduplicate", lambda articles: articles)
        monkeypatch.setattr(pipeline, "_cluster", lambda articles: (articles, []))
        monkeypatch.setattr(pipeline, "_rank", lambda articles, clusters: articles)
        monkeypatch.setattr(pipeline, "_diversify", lambda articles, limit=None: articles)
        monkeypatch.setattr(pipeline, "_summarize", lambda articles: articles)

        result = pipeline.run(limit=10)

        assert len(result.articles) == 1
        article = result.articles[0]
        assert article.title == "Lead Story Headline"
        assert article.candidate_strategy == "section_frontpage"
        assert article.source_type == "publisher_section"
        assert article.source_rank_position == 1
        assert article.source_section == ".lead-story"
        assert article.source_curated_flag is False
        assert article.source_official_flag is False

    def test_pipeline_weak_latest_source_does_not_flood_final_output(self, monkeypatch):
        config = Config(
            sources=[
                Source(
                    name="Weak Latest Feed",
                    url="https://example.com/weak.xml",
                    type="rss",
                    source_type="plain_rss",
                    candidate_strategy="latest",
                ),
                Source(
                    name="Strong Editorial",
                    url="https://example.com/strong",
                    type="html",
                    source_type="curated_editorial",
                    candidate_strategy="curated",
                ),
            ],
            thresholds={
                "similarity": 0.8,
                "min_score": 0.0,
                "cluster_size": 1,
                "max_per_source": 0,
                "weak_source_max_per_source": 1,
                "weak_source_recency_window_hours": 0.0,
                "corroboration_min_sources": 2,
            },
        )
        pipeline = NewsPipeline(config)
        now = datetime(2026, 3, 12)
        weak_articles = [
            Article(
                id=f"weak-{i}",
                title=f"Weak {i}",
                content="weak content",
                url=f"https://example.com/weak-{i}",
                source="Weak Latest Feed",
                published_at=now,
                score=1.0 - i * 0.01,
            )
            for i in range(4)
        ]
        strong_articles = [
            Article(
                id=f"strong-{i}",
                title=f"Strong {i}",
                content="strong content",
                url=f"https://example.com/strong-{i}",
                source="Strong Editorial",
                published_at=now,
                score=0.8 - i * 0.01,
            )
            for i in range(2)
        ]
        ranked_articles = weak_articles + strong_articles

        monkeypatch.setattr(pipeline, "_fetch", lambda sources, since: ranked_articles)
        monkeypatch.setattr(pipeline, "_normalize", lambda articles: articles)
        monkeypatch.setattr(pipeline, "_deduplicate", lambda articles: articles)
        monkeypatch.setattr(pipeline, "_cluster", lambda articles: (articles, []))
        monkeypatch.setattr(pipeline, "_rank", lambda articles, clusters: articles)
        monkeypatch.setattr(pipeline, "_summarize", lambda articles: articles)

        result = pipeline.run(limit=3)

        assert [article.source for article in result.articles] == [
            "Strong Editorial",
            "Weak Latest Feed",
            "Strong Editorial",
        ]

    def test_pipeline_filters_uncorroborated_corroboration_only_articles(self, monkeypatch):
        config = Config(
            sources=[
                Source(
                    name="Weak Corroboration",
                    url="https://example.com/weak.xml",
                    type="rss",
                    source_type="plain_rss",
                    candidate_strategy="corroboration_only",
                ),
                Source(
                    name="Strong Editorial",
                    url="https://example.com/strong",
                    type="html",
                    source_type="curated_editorial",
                    candidate_strategy="curated",
                ),
            ],
            thresholds={
                "similarity": 0.8,
                "min_score": 0.0,
                "cluster_size": 1,
                "max_per_source": 0,
                "weak_source_max_per_source": 1,
                "weak_source_recency_window_hours": 0.0,
                "corroboration_min_sources": 2,
            },
        )
        pipeline = NewsPipeline(config)
        now = datetime(2026, 3, 12)
        corroborated_weak = Article(
            id="weak-corroborated",
            title="Corroborated weak article",
            content="weak content",
            url="https://example.com/weak-corroborated",
            source="Weak Corroboration",
            published_at=now,
            score=0.9,
            cluster_id="cluster-1",
        )
        uncorroborated_weak = Article(
            id="weak-uncorroborated",
            title="Uncorroborated weak article",
            content="weak content",
            url="https://example.com/weak-uncorroborated",
            source="Weak Corroboration",
            published_at=now,
            score=0.85,
            cluster_id="cluster-2",
        )
        strong_match = Article(
            id="strong-match",
            title="Strong corroborating article",
            content="strong content",
            url="https://example.com/strong-match",
            source="Strong Editorial",
            published_at=now,
            score=0.8,
            cluster_id="cluster-1",
        )
        ranked_articles = [corroborated_weak, uncorroborated_weak, strong_match]

        monkeypatch.setattr(pipeline, "_fetch", lambda sources, since: ranked_articles)
        monkeypatch.setattr(pipeline, "_normalize", lambda articles: articles)
        monkeypatch.setattr(pipeline, "_deduplicate", lambda articles: articles)
        monkeypatch.setattr(pipeline, "_cluster", lambda articles: (articles, []))
        monkeypatch.setattr(pipeline, "_rank", lambda articles, clusters: articles)
        monkeypatch.setattr(pipeline, "_summarize", lambda articles: articles)

        result = pipeline.run(limit=3)

        assert [article.id for article in result.articles] == [
            "strong-match",
            "weak-corroborated",
        ]

    def test_pipeline_recency_window_handles_timezone_aware_articles(self, monkeypatch):
        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                fixed = datetime(2026, 3, 12, 12, 0, tzinfo=timezone.utc)
                if tz is None:
                    return fixed.replace(tzinfo=None)
                return fixed.astimezone(tz)

        monkeypatch.setattr(pipeline_module, "datetime", FixedDateTime)
        config = Config(
            sources=[
                Source(
                    name="Weak Latest Feed",
                    url="https://example.com/weak.xml",
                    type="rss",
                    source_type="plain_rss",
                    candidate_strategy="latest",
                    recency_window_hours=2,
                )
            ]
        )
        pipeline = NewsPipeline(config)
        source_by_name = {source.name: source for source in config.sources}
        articles = [
            Article(
                id="recent-aware",
                title="Recent aware",
                content="content",
                url="https://example.com/recent-aware",
                source="Weak Latest Feed",
                published_at=datetime(2026, 3, 12, 5, 0, tzinfo=timezone(timedelta(hours=-5))),
            ),
            Article(
                id="stale-aware",
                title="Stale aware",
                content="content",
                url="https://example.com/stale-aware",
                source="Weak Latest Feed",
                published_at=datetime(2026, 3, 12, 3, 0, tzinfo=timezone(timedelta(hours=-5))),
            ),
        ]

        filtered = pipeline._filter_by_recency_window(articles, source_by_name)

        assert [article.id for article in filtered] == ["recent-aware"]

    def test_pipeline_per_source_limit_overrides_global_max_per_source(self):
        config = Config(
            sources=[
                Source(
                    name="Override Feed",
                    url="https://example.com/override.xml",
                    contribution_limit=4,
                ),
                Source(
                    name="Default Feed",
                    url="https://example.com/default.xml",
                ),
            ],
            thresholds={
                "similarity": 0.8,
                "min_score": 0.0,
                "cluster_size": 1,
                "max_per_source": 2,
            },
        )
        pipeline = NewsPipeline(config)
        now = datetime(2026, 3, 12)
        articles = [
            Article(
                id=f"override-{i}",
                title=f"Override {i}",
                content="content",
                url=f"https://example.com/override-{i}",
                source="Override Feed",
                published_at=now,
                score=1.0 - i * 0.01,
            )
            for i in range(4)
        ] + [
            Article(
                id=f"default-{i}",
                title=f"Default {i}",
                content="content",
                url=f"https://example.com/default-{i}",
                source="Default Feed",
                published_at=now,
                score=0.8 - i * 0.01,
            )
            for i in range(2)
        ]

        diversified = pipeline._diversify(articles, limit=6)

        assert [article.source for article in diversified] == [
            "Override Feed",
            "Default Feed",
            "Override Feed",
            "Default Feed",
            "Override Feed",
            "Override Feed",
        ]

    def test_pipeline_annotates_structured_selection_reasons(self, monkeypatch):
        config = Config(
            sources=[
                Source(
                    name="Official Blog",
                    url="https://official.example",
                    source_type="official_blog",
                    candidate_strategy="frontpage",
                ),
                Source(
                    name="Independent Wire",
                    url="https://wire.example",
                    source_type="plain_rss",
                    candidate_strategy="latest",
                    weak_source=False,
                ),
            ],
            thresholds={
                "similarity": 0.8,
                "min_score": 0.0,
                "cluster_size": 1,
                "max_per_source": 0,
                "corroboration_min_sources": 2,
            },
        )
        pipeline = NewsPipeline(config)
        now = datetime(2026, 3, 12)
        official_article = Article(
            id="official",
            title="Official confirms release",
            content="content",
            url="https://official.example/release",
            source="Official Blog",
            published_at=now,
            score=1.1,
            cluster_id="cluster-1",
            source_official_flag=True,
            source_curated_flag=True,
            source_rank_position=1,
            source_engagement_score=42.0,
        )
        corroborating_article = Article(
            id="wire",
            title="Wire confirms release",
            content="content",
            url="https://wire.example/release",
            source="Independent Wire",
            published_at=now,
            score=0.9,
            cluster_id="cluster-1",
        )

        monkeypatch.setattr(
            pipeline,
            "_fetch",
            lambda sources, since: [official_article, corroborating_article],
        )
        monkeypatch.setattr(pipeline, "_normalize", lambda articles: articles)
        monkeypatch.setattr(pipeline, "_deduplicate", lambda articles: articles)
        monkeypatch.setattr(pipeline, "_cluster", lambda articles: (articles, []))
        monkeypatch.setattr(
            pipeline,
            "_rank",
            lambda articles, clusters: [official_article, corroborating_article],
        )
        monkeypatch.setattr(pipeline, "_diversify", lambda articles, limit=None: articles)
        monkeypatch.setattr(pipeline, "_summarize", lambda articles: articles)

        result = pipeline.run(limit=10)

        assert result.articles[0].selection_reasons == [
            {"kind": "official_release"},
            {"kind": "curated_inclusion"},
            {"kind": "frontpage_rank", "position": 1},
            {"kind": "engagement_proxy", "value": 42.0},
            {"kind": "independent_source_corroboration", "source_count": 2},
        ]
        assert result.articles[0].selection_adjustments == []

    def test_pipeline_annotates_weak_source_downgrade_for_selected_article(self, monkeypatch):
        config = Config(
            sources=[
                Source(
                    name="Weak Feed",
                    url="https://weak.example/feed.xml",
                    source_type="plain_rss",
                    candidate_strategy="latest",
                    weak_source_weight_multiplier=0.5,
                )
            ],
            thresholds={
                "similarity": 0.8,
                "min_score": 0.0,
                "cluster_size": 1,
                "max_per_source": 0,
            },
        )
        pipeline = NewsPipeline(config)
        weak_article = Article(
            id="weak",
            title="Weak feed item",
            content="content",
            url="https://weak.example/item",
            source="Weak Feed",
            published_at=datetime(2026, 3, 12),
            score=0.4,
        )

        monkeypatch.setattr(pipeline, "_fetch", lambda sources, since: [weak_article])
        monkeypatch.setattr(pipeline, "_normalize", lambda articles: articles)
        monkeypatch.setattr(pipeline, "_deduplicate", lambda articles: articles)
        monkeypatch.setattr(pipeline, "_cluster", lambda articles: (articles, []))
        monkeypatch.setattr(pipeline, "_rank", lambda articles, clusters: articles)
        monkeypatch.setattr(pipeline, "_diversify", lambda articles, limit=None: articles)
        monkeypatch.setattr(pipeline, "_summarize", lambda articles: articles)

        result = pipeline.run(limit=10)

        assert result.articles[0].selection_reasons == []
        assert result.articles[0].selection_adjustments == [
            {"kind": "weak_source_downgrade", "multiplier": 0.5}
        ]
