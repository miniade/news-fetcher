"""
Core data models for news-fetcher application.

This module defines the main data structures used throughout the application,
including articles, clusters, sources, and configuration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Article:
    """
    Represents a single news article.

    Attributes:
        id: Unique identifier for the article
        title: Article title
        content: Full article content
        url: URL to the original article
        source: Source name where the article was fetched from
        published_at: Date and time when the article was published
        fetched_at: Date and time when the article was fetched
        author: Article author (if available)
        summary: Summary of the article (if available)
        embeddings: Numeric embeddings for the article content (for clustering)
        cluster_id: ID of the cluster this article belongs to
        score: Relevance score of the article
        candidate_strategy: Optional acquisition mode used to discover the candidate
        source_type: Optional source taxonomy carried from source configuration
        source_rank_position: Optional upstream rank/order position of the candidate
        source_section: Optional upstream section or selector associated with the candidate
        source_engagement_score: Optional engagement score from the upstream source
        source_comment_count: Optional comment count from the upstream source
        source_view_count: Optional view count from the upstream source
        source_like_count: Optional like count from the upstream source
        source_curated_flag: Optional signal that the upstream source is curated
        source_official_flag: Optional signal that the upstream source is official
        source_frontpage_timestamp: Optional timestamp describing when a candidate was observed
        acquisition_confidence: Optional confidence score for acquisition metadata
        item_type: Optional logical item type carried through the pipeline (e.g. article, github_project)
        item_metadata: Structured item-specific metadata for non-article candidates or enriched items
        selection_reasons: Structured reasons explaining why the item was selected
        selection_adjustments: Structured score adjustments applied during selection
    """

    id: str
    title: str
    content: str
    url: str
    source: str
    published_at: datetime
    fetched_at: datetime = field(default_factory=datetime.now)
    author: Optional[str] = None
    summary: Optional[str] = None
    embeddings: Optional[List[float]] = None
    cluster_id: Optional[str] = None
    score: float = 0.0
    candidate_strategy: Optional[str] = None
    source_type: Optional[str] = None
    source_rank_position: Optional[int] = None
    source_section: Optional[str] = None
    source_engagement_score: Optional[float] = None
    source_comment_count: Optional[int] = None
    source_view_count: Optional[int] = None
    source_like_count: Optional[int] = None
    source_curated_flag: Optional[bool] = None
    source_official_flag: Optional[bool] = None
    source_frontpage_timestamp: Optional[datetime] = None
    acquisition_confidence: Optional[float] = None
    item_type: Optional[str] = None
    item_metadata: Dict[str, Any] = field(default_factory=dict)
    selection_reasons: List[Dict[str, Any]] = field(default_factory=list)
    selection_adjustments: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Cluster:
    """
    Represents a cluster of similar articles.

    Attributes:
        id: Unique identifier for the cluster
        articles: List of articles in this cluster
        centroid: Centroid vector of the cluster
        representative_article: Most representative article in the cluster
    """

    id: str
    articles: List[Article] = field(default_factory=list)
    centroid: Optional[List[float]] = None
    representative_article: Optional[Article] = None


@dataclass
class Source:
    """
    Represents a news source configuration.

    Attributes:
        name: Name of the news source
        url: URL to the source's RSS feed or homepage
        weight: Importance weight of this source
        type: Type of source (rss or html)
        selector: Optional CSS selector for HTML sources
        source_type: Optional source taxonomy for acquisition planning
        candidate_strategy: Optional acquisition mode for candidate discovery
        weak_source: Optional override for weak-source handling
        weak_source_weight_multiplier: Optional score multiplier for weak-source fallback
        contribution_limit: Optional final-output cap for this source
        recency_window_hours: Optional age window for accepted candidates
    """

    name: str
    url: str
    weight: float = 1.0
    type: str = "rss"
    selector: Optional[str] = None
    # v1 keeps source taxonomy/config separate from actual acquisition behavior.
    # The current fetch pipeline ignores these until strategy-specific fetchers land.
    source_type: Optional[str] = None
    candidate_strategy: Optional[str] = None
    weak_source: Optional[bool] = None
    weak_source_weight_multiplier: Optional[float] = None
    contribution_limit: Optional[int] = None
    recency_window_hours: Optional[float] = None


@dataclass
class Config:
    """
    Main configuration for the news-fetcher application.

    Attributes:
        sources: List of configured news sources
        thresholds: Configuration thresholds (e.g., similarity, score)
        weights: Weighting configuration for scoring
    """

    sources: List[Source] = field(default_factory=list)
    thresholds: Dict[str, float] = field(
        default_factory=lambda: {
            "similarity": 0.8,
            "min_score": 0.3,
            "cluster_size": 2,
            "max_per_source": 3,
            "weak_source_max_per_source": 1,
            "weak_source_recency_window_hours": 0.0,
            "corroboration_min_sources": 2,
        }
    )
    weights: Dict[str, float] = field(
        default_factory=lambda: {
            "content": 0.6,
            "source": 0.2,
            "publish_time": 0.2,
        }
    )
