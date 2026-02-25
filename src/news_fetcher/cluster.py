"""
Article clustering module for news-fetcher.

This module provides functionality for clustering articles based on content similarity
using HDBSCAN clustering algorithm with TF-IDF embeddings.
"""

import uuid
from typing import List, Optional, Dict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from hdbscan import HDBSCAN

from .models import Article, Cluster


def compute_cluster_centroid(articles: List[Article]) -> np.ndarray:
    """
    Compute centroid vector of a cluster of articles.

    Args:
        articles: List of articles in the cluster

    Returns:
        Centroid vector as numpy array

    Raises:
        ValueError: If articles list is empty
        ValueError: If articles have no embeddings
    """
    if not articles:
        raise ValueError("Articles list cannot be empty")

    # Check if articles have embeddings
    valid_articles = []
    for article in articles:
        if article.embeddings is not None and len(article.embeddings) > 0:
            valid_articles.append(article)
        else:
            raise ValueError("Articles must have embeddings to compute centroid")

    # Convert embeddings to numpy array
    embeddings = np.array([article.embeddings for article in valid_articles])

    # Compute centroid (mean vector)
    centroid = np.mean(embeddings, axis=0)

    return centroid


def find_representative_article(cluster: Cluster) -> Optional[Article]:
    """
    Find the most representative article in a cluster.

    The representative article is determined by:
    1. Length of content (more comprehensive)
    2. Source reputation
    3. Publication time (most recent)

    Args:
        cluster: Cluster to find representative article for

    Returns:
        Most representative article, or None if cluster is empty

    Raises:
        ValueError: If cluster has no articles
    """
    if not cluster.articles:
        raise ValueError("Cluster has no articles")

    # Sort articles by priority: content length > source > published time
    sorted_articles = sorted(
        cluster.articles,
        key=lambda a: (
            len(a.content),  # Longer content first
            a.source,        # Source reputation (alphabetical as proxy)
            a.published_at,  # Most recent first
        ),
        reverse=True
    )

    return sorted_articles[0]


def calculate_cluster_similarity(cluster1: Cluster, cluster2: Cluster) -> float:
    """
    Calculate similarity between two clusters.

    Similarity is computed as the cosine similarity between cluster centroids.

    Args:
        cluster1: First cluster
        cluster2: Second cluster

    Returns:
        Cosine similarity between clusters (0.0 to 1.0)

    Raises:
        ValueError: If clusters have no centroid
    """
    if cluster1.centroid is None or cluster2.centroid is None:
        raise ValueError("Clusters must have centroids to compute similarity")

    # Convert to numpy arrays
    centroid1 = np.array(cluster1.centroid)
    centroid2 = np.array(cluster2.centroid)

    # Compute cosine similarity
    dot_product = np.dot(centroid1, centroid2)
    norm1 = np.linalg.norm(centroid1)
    norm2 = np.linalg.norm(centroid2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


class ArticleClusterer:
    """
    Main article clustering interface using HDBSCAN.

    This class provides methods to cluster articles based on content similarity
    using HDBSCAN clustering algorithm with TF-IDF embeddings.
    """

    def __init__(self, min_cluster_size: int = 2, min_samples: int = 1):
        """
        Initialize ArticleClusterer with HDBSCAN parameters.

        Args:
            min_cluster_size: Minimum number of articles to form a cluster (default: 2)
            min_samples: Minimum samples to consider as core point (default: 1)

        Raises:
            ValueError: If min_cluster_size < 1 or min_samples < 0
        """
        if min_cluster_size < 1:
            raise ValueError("min_cluster_size must be at least 1")
        if min_samples < 0:
            raise ValueError("min_samples must be at least 0")

        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=1000
        )
        self.clusterer = HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            metric="euclidean"
        )
        self.fitted = False

    def _compute_embeddings(self, articles: List[Article]) -> np.ndarray:
        """
        Compute TF-IDF embeddings for articles.

        Args:
            articles: List of articles to compute embeddings for

        Returns:
            TF-IDF embeddings as numpy array

        Raises:
            ValueError: If articles list is empty
            ValueError: If articles have no content
        """
        if not articles:
            raise ValueError("Articles list cannot be empty")

        # Extract text content from articles
        texts = []
        for article in articles:
            if not article.content or article.content.strip() == "":
                raise ValueError("Articles must have content to compute embeddings")
            texts.append(article.content)

        # Compute TF-IDF embeddings
        if not self.fitted:
            embeddings = self.vectorizer.fit_transform(texts)
            self.fitted = True
        else:
            embeddings = self.vectorizer.transform(texts)

        return embeddings.toarray()

    def fit(self, articles: List[Article]) -> List[Cluster]:
        """
        Cluster articles and return clusters.

        Args:
            articles: List of articles to cluster

        Returns:
            List of clusters

        Raises:
            ValueError: If articles list is empty
        """
        if not articles:
            raise ValueError("Articles list cannot be empty")

        # Compute embeddings
        embeddings = self._compute_embeddings(articles)

        # Store embeddings in articles
        for i, article in enumerate(articles):
            article.embeddings = embeddings[i].tolist()

        # Perform clustering
        labels = self.clusterer.fit_predict(embeddings)

        # Create clusters
        clusters: Dict[int, Cluster] = {}
        for i, label in enumerate(labels):
            article = articles[i]

            # Noise points have label -1, skip them
            if label == -1:
                continue

            # Create cluster if it doesn't exist
            if label not in clusters:
                cluster_id = str(uuid.uuid4())
                cluster = Cluster(id=cluster_id)
                clusters[label] = cluster

            # Add article to cluster
            cluster = clusters[label]
            cluster.articles.append(article)
            article.cluster_id = cluster.id

        # Compute centroids and representative articles
        for cluster in clusters.values():
            cluster.centroid = compute_cluster_centroid(cluster.articles).tolist()
            cluster.representative_article = find_representative_article(cluster)

        return list(clusters.values())

    def partial_fit(self, article: Article) -> Optional[Cluster]:
        """
        Online clustering for streaming articles.

        This method attempts to assign a new article to an existing cluster
        or creates a new cluster if no suitable match is found.

        Args:
            article: Article to cluster

        Returns:
            Cluster the article was assigned to, or None if not assigned

        Raises:
            ValueError: If article has no content
        """
        if not article.content or article.content.strip() == "":
            raise ValueError("Article must have content")

        # This is a simplified online clustering approach
        # For real online clustering, consider using algorithms like:
        # - MiniBatchKMeans
        # - OnlineHDBSCAN (experimental)
        # - Incremental clustering with cosine similarity thresholds

        return None  # Placeholder for full implementation

    def _assign_to_cluster(self, article: Article) -> Optional[str]:
        """
        Assign article to existing or new cluster.

        Args:
            article: Article to assign

        Returns:
            Cluster ID if assigned, or None

        Raises:
            ValueError: If article has no content or embeddings
        """
        if not article.content or article.content.strip() == "":
            raise ValueError("Article must have content")
        if not article.embeddings:
            raise ValueError("Article must have embeddings")

        # This is a placeholder for cluster assignment logic
        # For full implementation, compute similarity with existing clusters
        # and assign to most similar cluster if similarity > threshold

        return None


class ClusterManager:
    """
    Manage cluster lifecycle and operations.

    This class provides functionality to manage clusters, including
    creation, retrieval, update, and merging of clusters.
    """

    def __init__(self):
        """Initialize ClusterManager with empty cluster storage."""
        self.clusters: Dict[str, Cluster] = {}

    def add_cluster(self, cluster: Cluster) -> None:
        """
        Add a new cluster.

        Args:
            cluster: Cluster to add

        Raises:
            ValueError: If cluster is None
            ValueError: If cluster with same ID already exists
        """
        if cluster is None:
            raise ValueError("Cluster cannot be None")
        if cluster.id in self.clusters:
            raise ValueError(f"Cluster with ID {cluster.id} already exists")

        self.clusters[cluster.id] = cluster

    def get_cluster(self, cluster_id: str) -> Optional[Cluster]:
        """
        Get cluster by ID.

        Args:
            cluster_id: ID of the cluster to retrieve

        Returns:
            Cluster if found, None otherwise

        Raises:
            ValueError: If cluster_id is empty
        """
        if not cluster_id or cluster_id.strip() == "":
            raise ValueError("cluster_id cannot be empty")

        return self.clusters.get(cluster_id)

    def update_cluster(self, cluster_id: str, article: Article) -> None:
        """
        Add article to an existing cluster.

        Args:
            cluster_id: ID of the cluster to update
            article: Article to add

        Raises:
            ValueError: If cluster_id is empty
            ValueError: If article is None
            KeyError: If cluster ID not found
        """
        if not cluster_id or cluster_id.strip() == "":
            raise ValueError("cluster_id cannot be empty")
        if article is None:
            raise ValueError("Article cannot be None")

        if cluster_id not in self.clusters:
            raise KeyError(f"Cluster with ID {cluster_id} not found")

        cluster = self.clusters[cluster_id]
        cluster.articles.append(article)
        article.cluster_id = cluster_id

        # Update centroid and representative article
        cluster.centroid = compute_cluster_centroid(cluster.articles).tolist()
        cluster.representative_article = find_representative_article(cluster)

    def merge_clusters(self, cluster_id1: str, cluster_id2: str) -> Cluster:
        """
        Merge two clusters into one.

        Args:
            cluster_id1: ID of first cluster
            cluster_id2: ID of second cluster

        Returns:
            Merged cluster

        Raises:
            ValueError: If cluster IDs are empty or identical
            KeyError: If either cluster ID not found
        """
        if not cluster_id1 or cluster_id1.strip() == "":
            raise ValueError("cluster_id1 cannot be empty")
        if not cluster_id2 or cluster_id2.strip() == "":
            raise ValueError("cluster_id2 cannot be empty")
        if cluster_id1 == cluster_id2:
            raise ValueError("Cannot merge a cluster with itself")

        if cluster_id1 not in self.clusters:
            raise KeyError(f"Cluster with ID {cluster_id1} not found")
        if cluster_id2 not in self.clusters:
            raise KeyError(f"Cluster with ID {cluster_id2} not found")

        # Get clusters to merge
        cluster1 = self.clusters[cluster_id1]
        cluster2 = self.clusters[cluster_id2]

        # Create new merged cluster
        merged_id = str(uuid.uuid4())
        merged_cluster = Cluster(id=merged_id)
        merged_cluster.articles = cluster1.articles + cluster2.articles

        # Update cluster IDs for articles
        for article in merged_cluster.articles:
            article.cluster_id = merged_id

        # Compute centroid and representative article
        merged_cluster.centroid = compute_cluster_centroid(
            merged_cluster.articles
        ).tolist()
        merged_cluster.representative_article = find_representative_article(
            merged_cluster
        )

        # Remove original clusters from storage
        del self.clusters[cluster_id1]
        del self.clusters[cluster_id2]

        # Add merged cluster to storage
        self.clusters[merged_id] = merged_cluster

        return merged_cluster

    def get_all_clusters(self) -> List[Cluster]:
        """
        Get all clusters.

        Returns:
            List of all clusters
        """
        return list(self.clusters.values())
