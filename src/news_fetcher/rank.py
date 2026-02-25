"""
Article ranking module with hotness algorithm and scoring components.

This module provides functionality to rank news articles using a composite
scoring model that includes Reddit-style hotness, time decay, source authority,
and cross-source diversity.
"""

import math
from datetime import datetime
from typing import List, Dict, Callable, Optional
from .models import Article, Source, Cluster, Config


class ArticleRanker:
    """Main ranking interface for news articles."""

    def __init__(self, config: Config):
        """Initialize the article ranker with configuration.

        Args:
            config: Configuration object containing weights, thresholds, and sources
        """
        self.config = config
        self.domain_scores = self._build_domain_scores()

    def _build_domain_scores(self) -> Dict[str, float]:
        """Build domain authority scores from configuration.

        Returns:
            Dictionary mapping source names to their configured weights
        """
        domain_scores = {}
        for source in self.config.sources:
            domain_scores[source.name] = source.weight
        return domain_scores

    def rank(self, articles: List[Article]) -> List[Article]:
        """Rank articles and return sorted by composite score.

        Args:
            articles: List of articles to rank

        Returns:
            List of articles sorted in descending order of score
        """
        if not articles:
            return []

        # Calculate scores for each article
        scored_articles = []
        for article in articles:
            score = self._calculate_score(article)
            article.score = score
            scored_articles.append(article)

        # Sort by score descending
        return sorted(scored_articles, key=lambda x: x.score, reverse=True)

    def _calculate_score(self, article: Article) -> float:
        """Calculate composite score for an article.

        Args:
            article: Article to score

        Returns:
            Composite score combining all scoring components
        """
        # Get individual scores
        content_score = article.score  # Assume content score is pre-calculated
        hotness = self._calculate_hotness(article)
        source_weight = self._get_source_weight(article)
        cross_source_score = self._calculate_cross_source_score(article)

        # Default weights if not configured
        default_weights = {
            "content": 0.4,
            "hotness": 0.3,
            "source": 0.2,
            "cross_source": 0.1
        }
        weights = {**default_weights, **self.config.weights}

        # Combine scores
        return combine_scores(
            content_score=content_score,
            hotness=hotness,
            source_weight=source_weight,
            cross_source_score=cross_source_score,
            weights=weights
        )

    def _calculate_hotness(self, article: Article) -> float:
        """Calculate Reddit-style hotness score.

        Args:
            article: Article to score

        Returns:
            Hotness score
        """
        # For simplicity, assume net votes based on source weight and content length
        # In real implementation, this would come from user interactions
        net_votes = max(1, len(article.content) // 100) * self._get_source_weight(article)
        return calculate_hotness_score(
            upvotes=int(net_votes),
            downvotes=0,
            published_at=article.published_at
        )

    def _calculate_time_decay(self, article: Article) -> float:
        """Calculate exponential time decay factor.

        Args:
            article: Article to score

        Returns:
            Time decay factor (0-1)
        """
        return calculate_time_decay(article.published_at)

    def _get_source_weight(self, article: Article) -> float:
        """Get source authority weight for an article.

        Args:
            article: Article to score

        Returns:
            Source authority weight
        """
        # Find source in config
        source = next((s for s in self.config.sources if s.name == article.source), None)
        if source is None:
            source = Source(name=article.source, url="", weight=1.0)

        return calculate_source_authority(source, self.domain_scores)

    def _calculate_cross_source_score(self, article: Article) -> float:
        """Calculate cross-source diversity score for an article's cluster.

        Args:
            article: Article to score

        Returns:
            Cross-source score based on cluster coverage
        """
        # In real implementation, this would require access to the full cluster
        # For now, assume cluster size of 1 (single article)
        return 1.0


def calculate_hotness_score(
    upvotes: int,
    downvotes: int,
    published_at: datetime,
    gravity: float = 1.8
) -> float:
    """
    Calculate Reddit-style hotness score.

    Formula:
        score = log10(max(abs(net_votes), 1)) * sign(net_votes) +
                (published_seconds / gravity_factor)

    Args:
        upvotes: Number of upvotes
        downvotes: Number of downvotes
        published_at: Publication datetime
        gravity: Gravity factor controlling decay speed (default: 1.8)

    Returns:
        Hotness score
    """
    net_votes = upvotes - downvotes
    published_seconds = (datetime.now() - published_at).total_seconds()

    # Calculate score components
    magnitude = math.log10(max(abs(net_votes), 1))
    sign = 1 if net_votes > 0 else -1 if net_votes < 0 else 0
    time_component = published_seconds / gravity

    return magnitude * sign + time_component


def calculate_time_decay(published_at: datetime, half_life: float = 3600.0) -> float:
    """
    Calculate exponential time decay factor.

    Formula:
        decay = exp(-ln(2) * age_seconds / half_life)

    Args:
        published_at: Publication datetime
        half_life: Half-life in seconds (default: 3600 seconds = 1 hour)

    Returns:
        Decay factor between 0 and 1
    """
    age_seconds = (datetime.now() - published_at).total_seconds()
    return math.exp(-math.log(2) * age_seconds / half_life)


def calculate_source_authority(source: Source, domain_scores: Dict[str, float]) -> float:
    """
    Calculate source authority using PageRank-style scoring.

    Args:
        source: Source to evaluate
        domain_scores: Domain reputation scores

    Returns:
        Source authority weight
    """
    base_weight = source.weight
    domain_bonus = domain_scores.get(source.name, 0.0)
    return base_weight + domain_bonus


def calculate_cross_source_score(cluster: Cluster) -> float:
    """
    Calculate cross-source diversity score for a cluster.

    Formula:
        cluster_size_weight = 1 + log(cluster_size)
        unique_sources = count of unique sources in cluster
        diversity_bonus = unique_sources / cluster_size

    Args:
        cluster: Cluster to evaluate

    Returns:
        Cross-source score
    """
    cluster_size = len(cluster.articles)
    if cluster_size == 0:
        return 0.0

    unique_sources = len(set(article.source for article in cluster.articles))
    cluster_size_weight = 1 + math.log(cluster_size)
    diversity_bonus = unique_sources / cluster_size

    return cluster_size_weight * diversity_bonus


def combine_scores(
    content_score: float,
    hotness: float,
    source_weight: float,
    cross_source_score: float,
    weights: Dict[str, float]
) -> float:
    """
    Combine multiple scoring components using weighted sum.

    Args:
        content_score: Content relevance score
        hotness: Hotness score
        source_weight: Source authority weight
        cross_source_score: Cross-source diversity score
        weights: Dictionary of component weights

    Returns:
        Combined score
    """
    # Normalize individual scores to similar ranges
    normalized_content = min(content_score, 10) / 10
    normalized_hotness = min(hotness, 10) / 10
    normalized_source = min(source_weight, 2) / 2
    normalized_cross = min(cross_source_score, 2) / 2

    # Calculate weighted sum
    score = (
        weights.get("content", 0.4) * normalized_content +
        weights.get("hotness", 0.3) * normalized_hotness +
        weights.get("source", 0.2) * normalized_source +
        weights.get("cross_source", 0.1) * normalized_cross
    )

    return score
