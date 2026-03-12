"""
Article ranking module with hotness algorithm and scoring components.

This module provides functionality to rank news articles using a composite
scoring model that includes freshness, source authority, and cross-source
coverage.
"""

import math
from datetime import datetime
from typing import Dict, List

from .models import Article, Source, Cluster, Config


class ArticleRanker:
    """Main ranking interface for news articles."""

    def __init__(self, config: Config):
        """Initialize the article ranker with configuration."""
        self.config = config
        self.domain_scores = self._build_domain_scores()

    def _build_domain_scores(self) -> Dict[str, float]:
        """Build source authority scores from configuration."""
        return {source.name: source.weight for source in self.config.sources}

    def rank(self, articles: List[Article]) -> List[Article]:
        """Rank articles and return them sorted by composite score."""
        if not articles:
            return []

        scored_articles = []
        for article in articles:
            article.score = self._calculate_score(article)
            scored_articles.append(article)

        return sorted(scored_articles, key=lambda x: x.score, reverse=True)

    def _calculate_score(self, article: Article) -> float:
        """Calculate composite score for an article."""
        content_score = max(article.score, 0.0)
        publish_time_score = self._calculate_time_decay(article)
        source_weight = self._get_source_weight(article)
        cross_source_score = self._calculate_cross_source_score(article)

        default_weights = {
            "content": 0.4,
            "publish_time": 0.3,
            "source": 0.2,
            "cross_source": 0.1,
        }
        weights = {**default_weights, **self.config.weights}
        if "publish_time" not in self.config.weights and "hotness" in self.config.weights:
            weights["publish_time"] = self.config.weights["hotness"]

        return combine_scores(
            content_score=content_score,
            publish_time_score=publish_time_score,
            source_weight=source_weight,
            cross_source_score=cross_source_score,
            weights=weights,
        )

    def _calculate_hotness(self, article: Article) -> float:
        """Backward-compatible hotness helper built on freshness and source weight."""
        net_votes = max(1, len(article.content) // 100) * self._get_source_weight(article)
        return calculate_hotness_score(
            upvotes=int(net_votes),
            downvotes=0,
            published_at=article.published_at,
        )

    def _calculate_time_decay(self, article: Article) -> float:
        """Calculate exponential time decay factor."""
        return calculate_time_decay(article.published_at)

    def _get_source_weight(self, article: Article) -> float:
        """Get source authority weight for an article."""
        source = next((s for s in self.config.sources if s.name == article.source), None)
        if source is None:
            source = Source(name=article.source, url="", weight=1.0)
        return calculate_source_authority(source, self.domain_scores)

    def _calculate_cross_source_score(self, article: Article) -> float:
        """Calculate cross-source diversity score for an article's cluster."""
        return 1.0


def calculate_hotness_score(
    upvotes: int,
    downvotes: int,
    published_at: datetime,
    gravity: float = 1.8,
) -> float:
    """Calculate a bounded Reddit-style hotness score.

    Newer items score higher; older items decay instead of growing without bound.
    """
    net_votes = upvotes - downvotes
    age_hours = max((datetime.now() - published_at).total_seconds() / 3600.0, 0.0)
    magnitude = math.log10(max(abs(net_votes), 1))
    sign = 1 if net_votes > 0 else -1 if net_votes < 0 else 0
    return (sign * magnitude) / ((age_hours + 2.0) ** (gravity / 2.0))


def calculate_time_decay(published_at: datetime, half_life: float = 43200.0) -> float:
    """Calculate exponential freshness decay with a 12-hour half-life by default."""
    age_seconds = max((datetime.now() - published_at).total_seconds(), 0.0)
    return math.exp(-math.log(2) * age_seconds / half_life)


def calculate_source_authority(source: Source, domain_scores: Dict[str, float]) -> float:
    """Calculate source authority using configured weights."""
    return domain_scores.get(source.name, source.weight)


def calculate_cross_source_score(cluster: Cluster) -> float:
    """Calculate cross-source diversity score for a cluster."""
    cluster_size = len(cluster.articles)
    if cluster_size == 0:
        return 0.0

    unique_sources = len(set(article.source for article in cluster.articles))
    cluster_size_weight = 1 + math.log(cluster_size)
    diversity_bonus = unique_sources / cluster_size

    return cluster_size_weight * diversity_bonus


def combine_scores(
    content_score: float,
    publish_time_score: float,
    source_weight: float,
    cross_source_score: float,
    weights: Dict[str, float],
) -> float:
    """Combine multiple scoring components using weighted sum."""
    normalized_content = min(max(content_score, 0.0), 10.0) / 10.0
    normalized_publish_time = min(max(publish_time_score, 0.0), 1.0)
    normalized_source = min(max(source_weight, 0.0), 2.0) / 2.0
    normalized_cross = min(max(cross_source_score, 0.0), 2.0) / 2.0

    return (
        weights.get("content", 0.4) * normalized_content
        + weights.get("publish_time", 0.3) * normalized_publish_time
        + weights.get("source", 0.2) * normalized_source
        + weights.get("cross_source", 0.1) * normalized_cross
    )
