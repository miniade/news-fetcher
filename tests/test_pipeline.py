"""Tests for the main pipeline."""

from datetime import datetime

import responses

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
