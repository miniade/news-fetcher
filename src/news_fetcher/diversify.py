"""
Diversity selection module using Maximum Marginal Relevance (MMR) and other methods.

This module provides functionality to select diverse articles from a set of candidates
using MMR, greedy selection, and submodular optimization.
"""

from typing import List, Optional, Callable, Dict
import numpy as np
from .models import Article, Cluster


class DiversitySelector:
    """Main diversity selection interface."""

    def __init__(self, lambda_param: float = 0.6):
        """Initialize the diversity selector with MMR parameter.

        Args:
            lambda_param: MMR parameter (0 = max diversity, 1 = max relevance)
        """
        self.lambda_param = lambda_param

    def select(
        self,
        articles: List[Article],
        k: int,
        selected: Optional[List[Article]] = None
    ) -> List[Article]:
        """Select k diverse articles using MMR.

        Args:
            articles: List of candidate articles
            k: Number of articles to select
            selected: List of already selected articles (default: None)

        Returns:
            List of selected diverse articles
        """
        if k <= 0:
            return []

        if selected is None:
            selected = []

        return mmr_select(
            candidates=articles,
            selected=selected,
            k=k,
            lambda_param=self.lambda_param
        )

    def _compute_similarity_matrix(self, articles: List[Article]) -> np.ndarray:
        """Compute pairwise similarity matrix between articles.

        Args:
            articles: List of articles

        Returns:
            Pairwise similarity matrix (n x n)
        """
        n = len(articles)
        sim_matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(n):
                if i == j:
                    sim_matrix[i][j] = 1.0
                    continue

                sim_matrix[i][j] = self._compute_similarity(articles[i], articles[j])

        return sim_matrix

    def _compute_similarity(self, article1: Article, article2: Article) -> float:
        """Compute similarity between two articles using embeddings.

        Args:
            article1: First article
            article2: Second article

        Returns:
            Similarity score between 0 and 1
        """
        if article1.embeddings is None or article2.embeddings is None:
            return 0.0

        vec1 = np.array(article1.embeddings)
        vec2 = np.array(article2.embeddings)

        # Normalize vectors
        vec1 = vec1 / np.linalg.norm(vec1)
        vec2 = vec2 / np.linalg.norm(vec2)

        # Cosine similarity
        return np.dot(vec1, vec2)

    def _compute_mmr_score(self, relevance: float, max_similarity: float) -> float:
        """Compute MMR score for a candidate article.

        Args:
            relevance: Relevance score of the candidate
            max_similarity: Maximum similarity to already selected articles

        Returns:
            MMR score
        """
        return self.lambda_param * relevance - (1 - self.lambda_param) * max_similarity

    def _get_embeddings(self, article: Article) -> np.ndarray:
        """Get or compute article embeddings.

        Args:
            article: Article to get embeddings for

        Returns:
            Article embeddings as numpy array

        Raises:
            ValueError: If embeddings are not available
        """
        if article.embeddings is None:
            raise ValueError(f"Article {article.id} has no embeddings")

        return np.array(article.embeddings)


def mmr_select(
    candidates: List[Article],
    selected: List[Article],
    k: int,
    lambda_param: float = 0.6,
    similarity_fn: Optional[Callable] = None
) -> List[Article]:
    """
    Maximum Marginal Relevance (MMR) selection implementation.

    MMR balances relevance and diversity by selecting articles that are both
    relevant to the query and dissimilar to already selected articles.

    Args:
        candidates: List of candidate articles
        selected: List of already selected articles
        k: Number of additional articles to select
        lambda_param: MMR parameter (0 = max diversity, 1 = max relevance)
        similarity_fn: Custom similarity function (default: cosine similarity)

    Returns:
        List of selected articles
    """
    if k <= 0:
        return selected.copy()

    # Initialize with selected articles
    result = selected.copy()
    available = [a for a in candidates if a not in result]

    if not available:
        return result

    # Default similarity function using embeddings
    if similarity_fn is None:
        def similarity_fn(a1: Article, a2: Article) -> float:
            if a1.embeddings is None or a2.embeddings is None:
                return 0.0
            vec1 = np.array(a1.embeddings)
            vec2 = np.array(a2.embeddings)
            return np.dot(vec1 / np.linalg.norm(vec1), vec2 / np.linalg.norm(vec2))

    # Select k articles
    for _ in range(k):
        if not available:
            break

        best_score = -1.0
        best_article = None

        for candidate in available:
            # Relevance is the article's score
            relevance = candidate.score

            # Maximum similarity to already selected articles
            if result:
                max_sim = max(similarity_fn(candidate, a) for a in result)
            else:
                max_sim = 0.0

            # MMR score
            score = lambda_param * relevance - (1 - lambda_param) * max_sim

            if score > best_score:
                best_score = score
                best_article = candidate

        if best_article is not None:
            result.append(best_article)
            available.remove(best_article)

    return result


def greedy_diversity_select(
    candidates: List[Article],
    k: int,
    similarity_fn: Callable
) -> List[Article]:
    """
    Greedy diversity selection algorithm.

    Starts with the most relevant article and iteratively adds the article that
    is least similar to the current set.

    Args:
        candidates: List of candidate articles
        k: Number of articles to select
        similarity_fn: Similarity function

    Returns:
        List of selected diverse articles
    """
    if k <= 0 or not candidates:
        return []

    # Sort candidates by relevance descending
    sorted_candidates = sorted(candidates, key=lambda x: x.score, reverse=True)

    if k == 1:
        return [sorted_candidates[0]]

    selected = [sorted_candidates[0]]
    available = sorted_candidates[1:]

    for _ in range(1, k):
        if not available:
            break

        # Find article with minimum maximum similarity to selected
        best_article = None
        min_max_sim = float("inf")

        for candidate in available:
            max_sim = max(similarity_fn(candidate, a) for a in selected)
            if max_sim < min_max_sim:
                min_max_sim = max_sim
                best_article = candidate

        if best_article is not None:
            selected.append(best_article)
            available.remove(best_article)

    return selected


def submodular_select(
    candidates: List[Article],
    k: int,
    submodular_fn: Callable
) -> List[Article]:
    """
    Submodular optimization for diversity selection using greedy algorithm.

    Args:
        candidates: List of candidate articles
        k: Number of articles to select
        submodular_fn: Submodular function to maximize

    Returns:
        List of selected articles
    """
    if k <= 0 or not candidates:
        return []

    selected = []

    for _ in range(k):
        best_gain = -1.0
        best_article = None

        for candidate in candidates:
            if candidate in selected:
                continue

            # Calculate gain of adding this candidate
            current_gain = submodular_fn(selected + [candidate]) - submodular_fn(selected)

            if current_gain > best_gain:
                best_gain = current_gain
                best_article = candidate

        if best_article is not None:
            selected.append(best_article)
        else:
            break

    return selected


def balance_sources(articles: List[Article], k: int, min_per_source: int = 1) -> List[Article]:
    """
    Ensure source diversity by balancing article selection across sources.

    Args:
        articles: List of candidate articles
        k: Number of articles to select
        min_per_source: Minimum number of articles per source (default: 1)

    Returns:
        List of selected articles with balanced source representation
    """
    if k <= 0:
        return []

    # Group articles by source
    source_groups: Dict[str, List[Article]] = {}
    for article in articles:
        if article.source not in source_groups:
            source_groups[article.source] = []
        source_groups[article.source].append(article)

    # Sort each source's articles by relevance
    for source in source_groups:
        source_groups[source] = sorted(
            source_groups[source],
            key=lambda x: x.score,
            reverse=True
        )

    selected = []
    sources = list(source_groups.keys())
    source_index = 0

    # First, ensure minimum per source
    while len(selected) < k and source_index < len(sources):
        source = sources[source_index]
        group = source_groups[source]

        for i in range(min_per_source):
            if i < len(group) and len(selected) < k:
                selected.append(group[i])

        source_index += 1

    # Fill remaining slots with top-ranked from all sources
    remaining = k - len(selected)
    if remaining > 0:
        # Collect all articles not already selected
        all_available = []
        for source in sources:
            group = source_groups[source]
            for article in group[min_per_source:]:
                if article not in selected:
                    all_available.append(article)

        # Sort by relevance and take top remaining
        all_available = sorted(all_available, key=lambda x: x.score, reverse=True)
        selected.extend(all_available[:remaining])

    return selected


def balance_topics(clusters: List[Cluster], k: int) -> List[Article]:
    """
    Ensure topic diversity by selecting representatives from clusters.

    Args:
        clusters: List of topic clusters
        k: Number of articles to select

    Returns:
        List of selected articles with balanced topic representation
    """
    if k <= 0 or not clusters:
        return []

    # Sort clusters by importance (size * average score)
    sorted_clusters = sorted(
        clusters,
        key=lambda c: (
            len(c.articles),
            sum(a.score for a in c.articles) / max(1, len(c.articles))
        ),
        reverse=True
    )

    selected = []

    for cluster in sorted_clusters:
        if len(selected) >= k:
            break

        # Select representative article from cluster
        if cluster.representative_article is not None:
            selected.append(cluster.representative_article)
        else:
            # Fallback: select top-ranked article in cluster
            top_article = sorted(cluster.articles, key=lambda x: x.score, reverse=True)[0]
            selected.append(top_article)

    return selected
