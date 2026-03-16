"""
Diversity selection module using Maximum Marginal Relevance (MMR) and other methods.

This module provides functionality to select diverse articles from a set of candidates
using MMR, greedy selection, and source-balancing helpers.
"""

from typing import Callable, Dict, List, Optional

import numpy as np

from .models import Article, Cluster


class DiversitySelector:
    """Main diversity selection interface."""

    def __init__(self, lambda_param: float = 0.6):
        """Initialize the diversity selector with MMR parameter."""
        self.lambda_param = lambda_param

    def select(
        self,
        articles: List[Article],
        k: int,
        selected: Optional[List[Article]] = None,
        max_per_source: Optional[int] = None,
        per_source_limits: Optional[Dict[str, int]] = None,
    ) -> List[Article]:
        """Select k diverse articles.

        When ``max_per_source`` is provided, use a source-balanced round-robin
        selection on the already ranked candidate list. Otherwise fall back to
        MMR selection.
        """
        if k <= 0:
            return []

        if selected is None:
            selected = []

        if (
            (max_per_source is not None and max_per_source > 0)
            or per_source_limits is not None
        ):
            return round_robin_select(
                candidates=articles,
                selected=selected,
                k=k,
                max_per_source=max_per_source if max_per_source is not None and max_per_source > 0 else None,
                per_source_limits=per_source_limits,
            )

        return mmr_select(
            candidates=articles,
            selected=selected,
            k=k,
            lambda_param=self.lambda_param,
        )

    def _compute_similarity_matrix(self, articles: List[Article]) -> np.ndarray:
        """Compute pairwise similarity matrix between articles."""
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
        """Compute similarity between two articles using embeddings."""
        if article1.embeddings is None or article2.embeddings is None:
            return 0.0

        vec1 = np.array(article1.embeddings)
        vec2 = np.array(article2.embeddings)

        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        vec1 = vec1 / norm1
        vec2 = vec2 / norm2

        return float(np.dot(vec1, vec2))

    def _compute_mmr_score(self, relevance: float, max_similarity: float) -> float:
        """Compute MMR score for a candidate article."""
        return self.lambda_param * relevance - (1 - self.lambda_param) * max_similarity

    def _get_embeddings(self, article: Article) -> np.ndarray:
        """Get or compute article embeddings."""
        if article.embeddings is None:
            raise ValueError(f"Article {article.id} has no embeddings")

        return np.array(article.embeddings)


def mmr_select(
    candidates: List[Article],
    selected: List[Article],
    k: int,
    lambda_param: float = 0.6,
    similarity_fn: Optional[Callable] = None,
) -> List[Article]:
    """Maximum Marginal Relevance (MMR) selection implementation."""
    if k <= 0:
        return selected.copy()

    result = selected.copy()
    available = [a for a in candidates if a not in result]

    if not available:
        return result

    if similarity_fn is None:

        def similarity_fn(a1: Article, a2: Article) -> float:
            if a1.embeddings is None or a2.embeddings is None:
                return 0.0
            vec1 = np.array(a1.embeddings)
            vec2 = np.array(a2.embeddings)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return float(np.dot(vec1 / norm1, vec2 / norm2))

    for _ in range(k):
        if not available:
            break

        best_score = -1.0
        best_article = None

        for candidate in available:
            relevance = candidate.score
            if result:
                max_sim = max(similarity_fn(candidate, a) for a in result)
            else:
                max_sim = 0.0

            score = lambda_param * relevance - (1 - lambda_param) * max_sim
            if score > best_score:
                best_score = score
                best_article = candidate

        if best_article is not None:
            result.append(best_article)
            available.remove(best_article)

    return result


def round_robin_select(
    candidates: List[Article],
    selected: List[Article],
    k: int,
    max_per_source: Optional[int] = None,
    per_source_limits: Optional[Dict[str, int]] = None,
) -> List[Article]:
    """Select articles in score-preserving source rounds with an optional cap.

    Candidates are assumed to already be ranked. The selector walks sources in
    first-seen order, taking one article per source each round until ``k`` is
    reached. If the per-source cap prevents filling all slots, remaining slots
    are filled from the leftover ranked pool.
    """
    if k <= 0:
        return selected.copy()

    result = selected.copy()
    available = [a for a in candidates if a not in result]
    if not available:
        return result

    source_groups: Dict[str, List[Article]] = {}
    source_order: List[str] = []
    for article in available:
        if article.source not in source_groups:
            source_groups[article.source] = []
            source_order.append(article.source)
        source_groups[article.source].append(article)

    counts: Dict[str, int] = {}
    for article in result:
        counts[article.source] = counts.get(article.source, 0) + 1

    while len(result) < k:
        made_progress = False
        for source in source_order:
            if len(result) >= k:
                break
            source_limit = max_per_source if max_per_source is not None else -1
            if per_source_limits and source in per_source_limits:
                source_limit = per_source_limits[source]
            if source_limit >= 0 and counts.get(source, 0) >= source_limit:
                continue
            group = source_groups.get(source, [])
            if not group:
                continue
            article = group.pop(0)
            result.append(article)
            counts[source] = counts.get(source, 0) + 1
            made_progress = True

        if not made_progress:
            break

    if len(result) < k:
        leftovers: List[Article] = []
        for source in source_order:
            source_limit = max_per_source if max_per_source is not None else -1
            if per_source_limits and source in per_source_limits:
                source_limit = per_source_limits[source]
            remaining_capacity = max(0, source_limit - counts.get(source, 0))
            if source_limit < 0:
                remaining_capacity = len(source_groups.get(source, []))
            if remaining_capacity <= 0:
                continue
            leftovers.extend(source_groups.get(source, [])[:remaining_capacity])
        result.extend(leftovers[: max(0, k - len(result))])

    return result


def greedy_diversity_select(
    candidates: List[Article],
    k: int,
    similarity_fn: Callable,
) -> List[Article]:
    """Greedy diversity selection algorithm."""
    if k <= 0 or not candidates:
        return []

    sorted_candidates = sorted(candidates, key=lambda x: x.score, reverse=True)

    if k == 1:
        return [sorted_candidates[0]]

    selected = [sorted_candidates[0]]
    available = sorted_candidates[1:]

    for _ in range(1, k):
        if not available:
            break

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
    submodular_fn: Callable,
) -> List[Article]:
    """Submodular optimization for diversity selection using greedy algorithm."""
    if k <= 0 or not candidates:
        return []

    selected = []

    for _ in range(k):
        best_gain = -1.0
        best_article = None

        for candidate in candidates:
            if candidate in selected:
                continue

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
    """Ensure source diversity by balancing article selection across sources."""
    if k <= 0:
        return []

    source_groups: Dict[str, List[Article]] = {}
    for article in articles:
        if article.source not in source_groups:
            source_groups[article.source] = []
        source_groups[article.source].append(article)

    for source in source_groups:
        source_groups[source] = sorted(
            source_groups[source],
            key=lambda x: x.score,
            reverse=True,
        )

    selected = []
    sources = list(source_groups.keys())
    source_index = 0

    while len(selected) < k and source_index < len(sources):
        source = sources[source_index]
        group = source_groups[source]

        for i in range(min_per_source):
            if i < len(group) and len(selected) < k:
                selected.append(group[i])

        source_index += 1

    remaining = k - len(selected)
    if remaining > 0:
        all_available = []
        for source in sources:
            group = source_groups[source]
            for article in group[min_per_source:]:
                if article not in selected:
                    all_available.append(article)

        all_available = sorted(all_available, key=lambda x: x.score, reverse=True)
        selected.extend(all_available[:remaining])

    return selected


def balance_topics(clusters: List[Cluster], k: int) -> List[Article]:
    """Ensure topic diversity by selecting representatives from clusters."""
    if k <= 0 or not clusters:
        return []

    sorted_clusters = sorted(
        clusters,
        key=lambda c: (
            len(c.articles),
            sum(a.score for a in c.articles) / max(1, len(c.articles)),
        ),
        reverse=True,
    )

    selected = []

    for cluster in sorted_clusters:
        if len(selected) >= k:
            break

        if cluster.representative_article is not None:
            selected.append(cluster.representative_article)
        else:
            top_article = sorted(cluster.articles, key=lambda x: x.score, reverse=True)[0]
            selected.append(top_article)

    return selected
