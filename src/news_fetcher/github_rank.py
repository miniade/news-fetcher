"""Rule-based ranking for GitHub project discovery candidates."""

from __future__ import annotations

import math
from typing import Any, Dict, List

from .models import Article


def rank_github_projects(articles: List[Article]) -> List[Article]:
    """Rank github_project candidates with a simple, explainable composite score."""
    ranked: List[Article] = []
    for article in articles:
        if article.item_type != "github_project":
            ranked.append(article)
            continue

        growth_score = _calculate_growth_score(article)
        activity_score = _calculate_activity_score(article)
        quality_score = _calculate_quality_score(article)

        discovery_score = (
            0.55 * growth_score
            + 0.25 * activity_score
            + 0.20 * quality_score
        )

        article.score = discovery_score
        article.item_metadata["discovery_score"] = discovery_score
        article.selection_reasons = _build_selection_reasons(article)
        article.selection_adjustments = _build_selection_adjustments(article)
        ranked.append(article)

    github_articles = [article for article in ranked if article.item_type == "github_project"]
    non_github_articles = [article for article in ranked if article.item_type != "github_project"]
    github_articles.sort(key=lambda article: article.score, reverse=True)
    return github_articles + non_github_articles


def _calculate_growth_score(article: Article) -> float:
    metadata = article.item_metadata or {}
    stars_today = metadata.get("stars_today") or 0
    if stars_today <= 0:
        return 0.0
    return min(math.log1p(stars_today) / math.log(2501.0), 1.0)


def _calculate_activity_score(article: Article) -> float:
    activity = (article.item_metadata or {}).get("activity_signals") or {}
    score = 0.0
    if activity.get("has_recent_push"):
        score += 0.5
    if activity.get("updated_recently"):
        score += 0.25

    forks_count = activity.get("forks_count") or 0
    watchers_count = activity.get("watchers_count") or 0
    score += min(math.log1p(max(forks_count, 0)) / math.log(501.0), 0.15)
    score += min(math.log1p(max(watchers_count, 0)) / math.log(501.0), 0.10)
    return min(score, 1.0)


def _calculate_quality_score(article: Article) -> float:
    quality = (article.item_metadata or {}).get("quality_signals") or {}
    signal_count = quality.get("quality_signal_count") or 0
    score = min(signal_count / 8.0, 1.0)
    if quality.get("is_not_fork") is False:
        score *= 0.85
    if quality.get("not_archived") is False:
        score *= 0.7
    if quality.get("not_disabled") is False:
        score *= 0.7
    return max(min(score, 1.0), 0.0)


def _build_selection_reasons(article: Article) -> List[Dict[str, Any]]:
    metadata = article.item_metadata or {}
    activity = metadata.get("activity_signals") or {}
    quality = metadata.get("quality_signals") or {}
    reasons: List[Dict[str, Any]] = []

    stars_today = metadata.get("stars_today")
    if stars_today:
        reasons.append({"kind": "github_stars_today", "stars_today": stars_today})

    if activity.get("has_recent_push"):
        reasons.append(
            {
                "kind": "recent_repo_push",
                "hours_since_push": activity.get("recent_push_age_hours"),
            }
        )

    if quality.get("quality_signal_count"):
        reasons.append(
            {
                "kind": "repo_quality_signals",
                "count": quality.get("quality_signal_count"),
            }
        )

    topics = metadata.get("topics") or []
    if topics:
        reasons.append({"kind": "repo_topics_present", "count": len(topics)})

    return reasons


def _build_selection_adjustments(article: Article) -> List[Dict[str, Any]]:
    quality = (article.item_metadata or {}).get("quality_signals") or {}
    adjustments: List[Dict[str, Any]] = []

    if quality.get("is_not_fork") is False:
        adjustments.append({"kind": "fork_penalty", "multiplier": 0.85})
    if quality.get("has_description") is False and quality.get("has_topics") is False:
        adjustments.append({"kind": "thin_metadata_penalty", "multiplier": 0.9})
    if quality.get("not_archived") is False:
        adjustments.append({"kind": "archived_penalty", "multiplier": 0.7})

    return adjustments
