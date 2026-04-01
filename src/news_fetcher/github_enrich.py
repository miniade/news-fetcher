"""GitHub project enrichment helpers for news-fetcher."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from .models import Article

_GITHUB_API_BASE = "https://api.github.com"


def enrich_github_projects(
    articles: List[Article],
    session: Optional[requests.Session] = None,
    timeout: int = 30,
) -> List[Article]:
    """Enrich github_project articles with repo metadata and derived signals."""
    if not articles:
        return []

    owns_session = session is None
    session = session or requests.Session()
    try:
        for article in articles:
            if article.item_type != "github_project":
                continue

            repo_full_name = _extract_repo_full_name(article)
            if not repo_full_name:
                continue

            payload = _fetch_repo_payload(repo_full_name, session=session, timeout=timeout)
            patch = _build_repo_enrichment(payload)
            article.item_metadata.update(patch)
        return articles
    finally:
        if owns_session:
            session.close()


def _extract_repo_full_name(article: Article) -> Optional[str]:
    repo_full_name = article.item_metadata.get("repo_full_name")
    if isinstance(repo_full_name, str) and "/" in repo_full_name:
        return repo_full_name
    return None


def _fetch_repo_payload(
    repo_full_name: str,
    session: requests.Session,
    timeout: int,
) -> Dict[str, Any]:
    response = session.get(
        f"{_GITHUB_API_BASE}/repos/{repo_full_name}",
        timeout=timeout,
        headers={"Accept": "application/vnd.github+json"},
    )
    response.raise_for_status()
    return response.json()


def _build_repo_enrichment(payload: Dict[str, Any]) -> Dict[str, Any]:
    stargazers_count = payload.get("stargazers_count")
    forks_count = payload.get("forks_count")
    watchers_count = payload.get("subscribers_count", payload.get("watchers_count"))
    open_issues_count = payload.get("open_issues_count")

    patch: Dict[str, Any] = {
        "description": payload.get("description"),
        "primary_language": payload.get("language"),
        "topics": payload.get("topics") or [],
        "stargazers_count": stargazers_count,
        "forks_count": forks_count,
        "watchers_count": watchers_count,
        "open_issues_count": open_issues_count,
        "license_spdx": ((payload.get("license") or {}).get("spdx_id")),
        "homepage": payload.get("homepage"),
        "default_branch": payload.get("default_branch"),
        "created_at": payload.get("created_at"),
        "updated_at": payload.get("updated_at"),
        "pushed_at": payload.get("pushed_at"),
        "archived": bool(payload.get("archived")),
        "disabled": bool(payload.get("disabled")),
        "fork": bool(payload.get("fork")),
        "activity_signals": _build_activity_signals(payload),
        "quality_signals": _build_quality_signals(payload),
    }
    return patch


def _build_activity_signals(payload: Dict[str, Any]) -> Dict[str, Any]:
    pushed_at = payload.get("pushed_at")
    recent_push_age_hours = _hours_since_iso8601(pushed_at)
    has_recent_push = recent_push_age_hours is not None and recent_push_age_hours <= 72
    updated_recently = _hours_since_iso8601(payload.get("updated_at"))
    updated_recently_flag = updated_recently is not None and updated_recently <= 72

    return {
        "recent_push_age_hours": recent_push_age_hours,
        "has_recent_push": has_recent_push,
        "updated_recently": updated_recently_flag,
        "open_issues_count": payload.get("open_issues_count"),
        "forks_count": payload.get("forks_count"),
        "watchers_count": payload.get("subscribers_count", payload.get("watchers_count")),
    }


def _build_quality_signals(payload: Dict[str, Any]) -> Dict[str, Any]:
    topics = payload.get("topics") or []
    license_obj = payload.get("license") or {}

    signals = {
        "has_description": bool(payload.get("description")),
        "has_topics": bool(topics),
        "has_license": bool(license_obj.get("spdx_id")),
        "has_homepage": bool(payload.get("homepage")),
        "not_archived": not bool(payload.get("archived")),
        "not_disabled": not bool(payload.get("disabled")),
        "is_not_fork": not bool(payload.get("fork")),
        "has_issues_enabled": bool(payload.get("has_issues")),
        "has_discussions_enabled": bool(payload.get("has_discussions")),
    }
    signals["quality_signal_count"] = sum(1 for value in signals.values() if value is True)
    return signals


def _hours_since_iso8601(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return max((datetime.now(timezone.utc) - dt).total_seconds() / 3600.0, 0.0)
