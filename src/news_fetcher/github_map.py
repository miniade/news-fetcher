"""Mapping helpers from GitHub project candidates to news-style articles."""

from __future__ import annotations

from typing import List

from .models import Article


def map_github_projects_to_news_items(articles: List[Article]) -> List[Article]:
    """Map ranked GitHub project candidates into news-style Article objects."""
    mapped: List[Article] = []
    for article in articles:
        if article.item_type != "github_project":
            mapped.append(article)
            continue
        mapped.append(_map_github_project(article))
    return mapped


def _map_github_project(article: Article) -> Article:
    metadata = article.item_metadata or {}
    repo_name = metadata.get("name") or article.title.split("/")[-1]
    title = f"GitHub 项目 {repo_name} 今日快速走热"
    rationale = _render_reason_summary(article)

    description = metadata.get("description") or article.content or article.title
    summary = f"{description} {rationale}".strip()
    content = f"{description}\n\n{rationale}".strip()

    mapped_metadata = dict(metadata)
    mapped_metadata["news_title"] = title
    mapped_metadata["news_summary"] = summary

    return Article(
        id=f"news-{article.id}",
        title=title,
        content=content,
        url=article.url,
        source=article.source,
        published_at=article.published_at,
        fetched_at=article.fetched_at,
        author=article.author,
        summary=summary,
        score=article.score,
        candidate_strategy=article.candidate_strategy,
        source_type=article.source_type,
        source_rank_position=article.source_rank_position,
        source_section=article.source_section,
        source_engagement_score=article.source_engagement_score,
        source_comment_count=article.source_comment_count,
        source_view_count=article.source_view_count,
        source_like_count=article.source_like_count,
        source_curated_flag=article.source_curated_flag,
        source_official_flag=article.source_official_flag,
        source_frontpage_timestamp=article.source_frontpage_timestamp,
        acquisition_confidence=article.acquisition_confidence,
        item_type=article.item_type,
        item_metadata=mapped_metadata,
        selection_reasons=list(article.selection_reasons),
        selection_adjustments=list(article.selection_adjustments),
    )


def _render_reason_summary(article: Article) -> str:
    phrases: List[str] = []
    for reason in article.selection_reasons:
        kind = reason.get("kind")
        if kind == "github_stars_today":
            stars_today = reason.get("stars_today")
            if stars_today:
                phrases.append(f"今天 star 增长明显（+{stars_today}）")
            else:
                phrases.append("今天 star 增长明显")
        elif kind == "recent_repo_push":
            phrases.append("近期仍有活跃更新")
        elif kind == "repo_quality_signals":
            phrases.append("项目资料与基础质量信号较完整")
        elif kind == "repo_topics_present":
            phrases.append("主题定位相对清晰")

    if not phrases:
        return "今天值得关注。"

    joined = "，".join(phrases)
    return f"{joined}。"
