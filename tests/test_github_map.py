"""Tests for GitHub project candidate to news item mapping."""

from datetime import datetime, timezone

from news_fetcher.github_map import map_github_projects_to_news_items
from news_fetcher.models import Article


class TestGitHubMap:
    def test_map_github_projects_to_news_items_generates_news_like_title_and_summary(self):
        article = Article(
            id="github-1",
            title="miniade/news-fetcher",
            content="A news aggregation and clustering tool.",
            url="https://github.com/miniade/news-fetcher",
            source="GitHub Trending",
            published_at=datetime.now(timezone.utc),
            score=0.82,
            item_type="github_project",
            item_metadata={
                "name": "news-fetcher",
                "description": "A news aggregation and clustering tool.",
            },
            selection_reasons=[
                {"kind": "github_stars_today", "stars_today": 42},
                {"kind": "recent_repo_push", "hours_since_push": 6.0},
                {"kind": "repo_quality_signals", "count": 6},
            ],
        )

        mapped = map_github_projects_to_news_items([article])[0]

        assert mapped.title == "GitHub 项目 news-fetcher 今日快速走热"
        assert mapped.summary is not None
        assert "A news aggregation and clustering tool." in mapped.summary
        assert "今天 star 增长明显" in mapped.summary
        assert "近期仍有活跃更新" in mapped.summary
        assert mapped.item_metadata["news_title"] == mapped.title
        assert mapped.item_metadata["news_summary"] == mapped.summary

    def test_map_github_projects_to_news_items_preserves_score_and_reasons(self):
        article = Article(
            id="github-2",
            title="example/repo",
            content="repo desc",
            url="https://github.com/example/repo",
            source="GitHub Trending",
            published_at=datetime.now(timezone.utc),
            score=0.66,
            item_type="github_project",
            item_metadata={"name": "repo", "description": "repo desc"},
            selection_reasons=[{"kind": "github_stars_today", "stars_today": 88}],
            selection_adjustments=[{"kind": "fork_penalty", "multiplier": 0.85}],
        )

        mapped = map_github_projects_to_news_items([article])[0]

        assert mapped.id == "news-github-2"
        assert mapped.score == 0.66
        assert mapped.selection_reasons == [{"kind": "github_stars_today", "stars_today": 88}]
        assert mapped.selection_adjustments == [{"kind": "fork_penalty", "multiplier": 0.85}]
        assert mapped.item_type == "github_project"

    def test_map_github_projects_to_news_items_leaves_non_github_articles_unchanged(self):
        article = Article(
            id="plain-1",
            title="Plain Article",
            content="content",
            url="https://example.com/story",
            source="Example",
            published_at=datetime.now(timezone.utc),
        )

        mapped = map_github_projects_to_news_items([article])[0]

        assert mapped.title == "Plain Article"
        assert mapped.item_type is None
