"""Tests for GitHub project enrichment helpers."""

from datetime import datetime, timezone, timedelta

import responses

from news_fetcher.github_enrich import enrich_github_projects
from news_fetcher.models import Article


class TestGitHubEnrich:
    def test_enrich_github_projects_keeps_non_github_articles_unchanged(self):
        article = Article(
            id="plain-1",
            title="Plain Article",
            content="content",
            url="https://example.com/story",
            source="Example",
            published_at=datetime.now(timezone.utc),
        )

        results = enrich_github_projects([article])

        assert results[0].item_metadata == {}
        assert results[0].item_type is None

    @responses.activate
    def test_enrich_github_projects_adds_repo_metadata_and_signals(self):
        now = datetime.now(timezone.utc)
        responses.add(
            responses.GET,
            "https://api.github.com/repos/miniade/news-fetcher",
            json={
                "description": "A news aggregation and clustering tool",
                "language": "Python",
                "topics": ["news", "clawhub", "github"],
                "stargazers_count": 123,
                "forks_count": 17,
                "subscribers_count": 11,
                "open_issues_count": 5,
                "license": {"spdx_id": "MIT"},
                "homepage": "https://example.com/news-fetcher",
                "default_branch": "main",
                "created_at": "2025-02-25T00:00:00Z",
                "updated_at": (now - timedelta(hours=4)).isoformat().replace("+00:00", "Z"),
                "pushed_at": (now - timedelta(hours=6)).isoformat().replace("+00:00", "Z"),
                "archived": False,
                "disabled": False,
                "fork": False,
                "has_issues": True,
                "has_discussions": True,
            },
            status=200,
        )

        article = Article(
            id="github-1",
            title="miniade/news-fetcher",
            content="desc",
            url="https://github.com/miniade/news-fetcher",
            source="GitHub Trending",
            published_at=now,
            item_type="github_project",
            item_metadata={
                "repo_full_name": "miniade/news-fetcher",
                "stars_today": 42,
                "growth_signals": {"stars_today": 42},
            },
        )

        results = enrich_github_projects([article])
        enriched = results[0]

        assert enriched.item_metadata["primary_language"] == "Python"
        assert enriched.item_metadata["license_spdx"] == "MIT"
        assert enriched.item_metadata["topics"] == ["news", "clawhub", "github"]
        assert enriched.item_metadata["stargazers_count"] == 123
        assert enriched.item_metadata["forks_count"] == 17
        assert enriched.item_metadata["watchers_count"] == 11
        assert enriched.item_metadata["activity_signals"]["has_recent_push"] is True
        assert enriched.item_metadata["quality_signals"]["has_description"] is True
        assert enriched.item_metadata["quality_signals"]["has_topics"] is True
        assert enriched.item_metadata["quality_signals"]["quality_signal_count"] >= 1
        assert enriched.item_metadata["growth_signals"]["stars_today"] == 42

    @responses.activate
    def test_enrich_github_projects_handles_missing_optional_fields(self):
        responses.add(
            responses.GET,
            "https://api.github.com/repos/example/minimal",
            json={
                "description": None,
                "language": None,
                "topics": [],
                "stargazers_count": 10,
                "forks_count": 1,
                "watchers_count": 10,
                "open_issues_count": 0,
                "license": None,
                "homepage": "",
                "default_branch": "main",
                "created_at": "2025-02-25T00:00:00Z",
                "updated_at": "2025-02-25T00:00:00Z",
                "pushed_at": "2025-02-25T00:00:00Z",
                "archived": False,
                "disabled": False,
                "fork": False,
                "has_issues": True,
                "has_discussions": False,
            },
            status=200,
        )

        article = Article(
            id="github-2",
            title="example/minimal",
            content="desc",
            url="https://github.com/example/minimal",
            source="GitHub Trending",
            published_at=datetime.now(timezone.utc),
            item_type="github_project",
            item_metadata={"repo_full_name": "example/minimal"},
        )

        results = enrich_github_projects([article])
        enriched = results[0]

        assert enriched.item_metadata["license_spdx"] is None
        assert enriched.item_metadata["topics"] == []
        assert enriched.item_metadata["quality_signals"]["has_license"] is False
        assert enriched.item_metadata["quality_signals"]["has_topics"] is False
