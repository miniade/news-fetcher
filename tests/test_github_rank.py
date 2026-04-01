"""Tests for GitHub project ranking."""

from datetime import datetime, timezone

from news_fetcher.github_rank import rank_github_projects
from news_fetcher.models import Article


class TestGitHubRank:
    def _article(
        self,
        *,
        article_id: str,
        stars_today: int,
        has_recent_push: bool,
        updated_recently: bool,
        forks_count: int,
        watchers_count: int,
        quality_signal_count: int,
        topics=None,
        is_not_fork: bool = True,
        has_description: bool = True,
        has_topics: bool = True,
        not_archived: bool = True,
        not_disabled: bool = True,
    ):
        return Article(
            id=article_id,
            title=article_id,
            content=article_id,
            url=f"https://github.com/example/{article_id}",
            source="GitHub Trending",
            published_at=datetime.now(timezone.utc),
            item_type="github_project",
            item_metadata={
                "repo_full_name": f"example/{article_id}",
                "stars_today": stars_today,
                "topics": topics or [],
                "activity_signals": {
                    "has_recent_push": has_recent_push,
                    "updated_recently": updated_recently,
                    "recent_push_age_hours": 6.0 if has_recent_push else 200.0,
                    "forks_count": forks_count,
                    "watchers_count": watchers_count,
                },
                "quality_signals": {
                    "quality_signal_count": quality_signal_count,
                    "is_not_fork": is_not_fork,
                    "has_description": has_description,
                    "has_topics": has_topics,
                    "not_archived": not_archived,
                    "not_disabled": not_disabled,
                },
            },
        )

    def test_rank_github_projects_prefers_growth_activity_and_quality_together(self):
        strong = self._article(
            article_id="strong",
            stars_today=1200,
            has_recent_push=True,
            updated_recently=True,
            forks_count=120,
            watchers_count=80,
            quality_signal_count=7,
            topics=["ai", "agent"],
        )
        weak = self._article(
            article_id="weak",
            stars_today=300,
            has_recent_push=False,
            updated_recently=False,
            forks_count=5,
            watchers_count=2,
            quality_signal_count=2,
            topics=[],
        )

        ranked = rank_github_projects([weak, strong])

        assert ranked[0].id == "strong"
        assert ranked[0].score > ranked[1].score

    def test_rank_github_projects_penalizes_thin_fork_like_candidates(self):
        high_growth_but_thin = self._article(
            article_id="thin-fork",
            stars_today=1500,
            has_recent_push=False,
            updated_recently=False,
            forks_count=1,
            watchers_count=1,
            quality_signal_count=1,
            topics=[],
            is_not_fork=False,
            has_description=False,
            has_topics=False,
        )
        balanced = self._article(
            article_id="balanced",
            stars_today=900,
            has_recent_push=True,
            updated_recently=True,
            forks_count=40,
            watchers_count=20,
            quality_signal_count=6,
            topics=["python"],
        )

        ranked = rank_github_projects([high_growth_but_thin, balanced])

        assert ranked[0].id == "balanced"
        assert any(adj["kind"] == "fork_penalty" for adj in high_growth_but_thin.selection_adjustments)
        assert any(adj["kind"] == "thin_metadata_penalty" for adj in high_growth_but_thin.selection_adjustments)

    def test_rank_github_projects_writes_reasons_and_discovery_score(self):
        article = self._article(
            article_id="explained",
            stars_today=700,
            has_recent_push=True,
            updated_recently=True,
            forks_count=30,
            watchers_count=10,
            quality_signal_count=5,
            topics=["cli", "automation"],
        )

        ranked = rank_github_projects([article])
        enriched = ranked[0]

        assert enriched.item_metadata["discovery_score"] == enriched.score
        kinds = {reason["kind"] for reason in enriched.selection_reasons}
        assert "github_stars_today" in kinds
        assert "recent_repo_push" in kinds
        assert "repo_quality_signals" in kinds
        assert "repo_topics_present" in kinds
