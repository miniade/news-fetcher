"""Tests for the main pipeline."""

from datetime import datetime

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
