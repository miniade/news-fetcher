"""
Core data models for news-fetcher application.

This module defines the main data structures used throughout the application,
including articles, clusters, sources, and configuration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict


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
    """

    name: str
    url: str
    weight: float = 1.0
    type: str = "rss"


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
            "min_score": 0.5,
            "cluster_size": 2,
            "max_per_source": 3,
        }
    )
    weights: Dict[str, float] = field(
        default_factory=lambda: {
            "content": 0.6,
            "source": 0.2,
            "publish_time": 0.2,
        }
    )
