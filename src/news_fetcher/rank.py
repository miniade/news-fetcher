"""
Article ranking module with hotness algorithm and scoring components.

This module ranks articles with article-level signals first, then applies a
bounded event-level lift when a cluster is corroborated across independent
sources.
"""

import math
from datetime import datetime
from typing import Dict, List, Optional

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

    def rank(
        self,
        articles: List[Article],
        clusters: Optional[List[Cluster]] = None,
    ) -> List[Article]:
        """Rank articles and return them sorted by composite score."""
        if not articles:
            return []

        cluster_lookup = self._build_cluster_lookup(articles, clusters)
        scored_articles = []
        for article in articles:
            article.score = self._calculate_score(
                article,
                cluster=cluster_lookup.get(article.cluster_id),
            )
            scored_articles.append(article)

        return sorted(scored_articles, key=lambda x: x.score, reverse=True)

    def _build_cluster_lookup(
        self,
        articles: List[Article],
        clusters: Optional[List[Cluster]],
    ) -> Dict[str, Cluster]:
        """Build cluster lookup keyed by cluster id for event-level scoring."""
        cluster_lookup: Dict[str, Cluster] = {}
        for cluster in clusters or []:
            cluster_lookup[cluster.id] = cluster

        grouped_articles: Dict[str, List[Article]] = {}
        for article in articles:
            if article.cluster_id:
                grouped_articles.setdefault(article.cluster_id, []).append(article)

        for cluster_id, cluster_articles in grouped_articles.items():
            cluster_lookup.setdefault(cluster_id, Cluster(id=cluster_id, articles=cluster_articles))

        return cluster_lookup

    def _calculate_score(self, article: Article, cluster: Optional[Cluster] = None) -> float:
        """Calculate composite score for an article."""
        content_score = max(article.score, 0.0)
        publish_time_score = self._calculate_time_decay(article)
        source_weight = self._get_source_weight(article)
        acquisition_score = self._calculate_acquisition_score(article)
        cross_source_score = self._calculate_cross_source_score(cluster)

        default_weights = {
            # Article-level score remains primary; cluster lift is additive.
            "content": 0.35,
            "publish_time": 0.25,
            "source": 0.2,
            "acquisition": 0.1,
            "cross_source": 0.1,
        }
        weights = {**default_weights, **self.config.weights}
        if "publish_time" not in self.config.weights and "hotness" in self.config.weights:
            weights["publish_time"] = self.config.weights["hotness"]

        return combine_scores(
            content_score=content_score,
            publish_time_score=publish_time_score,
            source_weight=source_weight,
            acquisition_score=acquisition_score,
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

    def _calculate_acquisition_score(self, article: Article) -> float:
        """Calculate bounded score from acquisition metadata when available."""
        base_score = calculate_acquisition_score(article)
        if article.acquisition_confidence is None:
            return base_score

        confidence = min(max(article.acquisition_confidence, 0.0), 1.0)
        return base_score * (0.5 + 0.5 * confidence)

    def _calculate_cross_source_score(self, cluster: Optional[Cluster]) -> float:
        """Calculate corroboration score from the article's cluster when present."""
        if cluster is None:
            return 0.0

        min_sources = int(self.config.thresholds.get("corroboration_min_sources", 2) or 2)
        return calculate_cross_source_score(cluster, min_independent_sources=min_sources)


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


def calculate_acquisition_score(article: Article) -> float:
    """Calculate a bounded article-level boost from acquisition metadata."""
    score = 0.0

    if article.source_official_flag:
        score += 0.45
    if article.source_curated_flag:
        score += 0.3
    if article.source_rank_position is not None and article.source_rank_position > 0:
        score += min(1.0 / math.sqrt(article.source_rank_position), 0.8)

    engagement_proxy = 0.0
    if article.source_engagement_score is not None:
        engagement_proxy = max(article.source_engagement_score, 0.0)
    else:
        if article.source_comment_count:
            engagement_proxy += article.source_comment_count * 3.0
        if article.source_like_count:
            engagement_proxy += article.source_like_count * 2.0
        if article.source_view_count:
            engagement_proxy += article.source_view_count / 1000.0

    if engagement_proxy > 0:
        score += min(math.log1p(engagement_proxy) / math.log(101.0), 1.0)

    return min(score, 2.0)


def calculate_cross_source_score(
    cluster: Cluster,
    min_independent_sources: int = 2,
) -> float:
    """Calculate bounded cluster corroboration score from independent sources."""
    cluster_size = len(cluster.articles)
    if cluster_size == 0:
        return 0.0

    unique_sources = len(set(article.source for article in cluster.articles))
    if unique_sources < min_independent_sources:
        return 0.0

    corroboration_score = 1.0 + math.log1p(unique_sources - min_independent_sources + 1)
    repeated_coverage_bonus = 0.15 * math.log1p(max(cluster_size - unique_sources, 0))
    return min(corroboration_score + repeated_coverage_bonus, 2.0)


def combine_scores(
    content_score: float,
    publish_time_score: float,
    source_weight: float,
    acquisition_score: float,
    cross_source_score: float,
    weights: Dict[str, float],
) -> float:
    """Combine multiple scoring components using weighted sum."""
    normalized_content = min(max(content_score, 0.0), 10.0) / 10.0
    normalized_publish_time = min(max(publish_time_score, 0.0), 1.0)
    normalized_source = min(max(source_weight, 0.0), 2.0) / 2.0
    normalized_acquisition = min(max(acquisition_score, 0.0), 2.0) / 2.0
    normalized_cross = min(max(cross_source_score, 0.0), 2.0) / 2.0

    return (
        weights.get("content", 0.4) * normalized_content
        + weights.get("publish_time", 0.3) * normalized_publish_time
        + weights.get("source", 0.2) * normalized_source
        + weights.get("acquisition", 0.0) * normalized_acquisition
        + weights.get("cross_source", 0.1) * normalized_cross
    )
