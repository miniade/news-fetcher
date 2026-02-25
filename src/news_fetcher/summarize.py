"""
Article summarization module for news-fetcher application.

This module provides various article summarization algorithms and a unified
interface for generating summaries from news articles.
"""

import re
import math
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass
from collections import defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from news_fetcher.models import Article, Cluster


@dataclass
class SentenceInfo:
    """Data class to store sentence information for scoring."""
    index: int
    text: str
    position: int
    is_quote: bool
    has_stats: bool
    has_entities: bool
    score: float = 0.0


class ArticleSummarizer:
    """
    Main article summarization interface.

    Provides multiple summarization methods with a consistent API.
    """

    def __init__(self, method: str = "position", max_sentences: int = 3):
        """
        Initialize the ArticleSummarizer.

        Args:
            method: Summarization method to use. Options:
                - "position": Position-based summarization (default)
                - "textrank": TextRank algorithm
                - "lead": Lead-N sentences
                - "centroid": Centroid-based (for clusters)
            max_sentences: Maximum number of sentences to include in summaries
        """
        valid_methods = ["position", "textrank", "lead", "centroid"]
        if method not in valid_methods:
            raise ValueError(f"Invalid summarization method: {method}. "
                             f"Valid methods: {', '.join(valid_methods)}")
        self.method = method
        self.max_sentences = max_sentences

    def summarize(self, article: Article) -> str:
        """
        Generate a summary for a single article.

        Args:
            article: Article object to summarize

        Returns:
            Generated summary as string
        """
        return self.summarize_text(article.content, article.title)

    def summarize_text(self, text: str, title: str = "") -> str:
        """
        Generate a summary from raw text.

        Args:
            text: Text content to summarize
            title: Optional title for context

        Returns:
            Generated summary as string
        """
        if self.method == "position":
            return position_based_summary(text, self.max_sentences)
        elif self.method == "textrank":
            return textrank_summary(text, self.max_sentences)
        elif self.method == "lead":
            return lead_n_summary(text, self.max_sentences)
        elif self.method == "centroid":
            raise NotImplementedError("Centroid method requires a cluster")
        else:
            raise ValueError(f"Unknown summarization method: {self.method}")

    def extract_key_sentences(self, text: str, n: int = 3) -> List[str]:
        """
        Extract top N important sentences from text.

        Args:
            text: Text content to analyze
            n: Number of key sentences to extract

        Returns:
            List of top N important sentences
        """
        sentences = tokenize_sentences(text)
        if len(sentences) <= n:
            return sentences

        # Score sentences using position-based approach
        scored = []
        for i, sent in enumerate(sentences):
            info = _analyze_sentence(sent, i, len(sentences))
            scored.append(info)

        # Sort by score and take top N
        scored.sort(key=lambda x: x.score, reverse=True)
        top_n = scored[:n]

        # Sort by original position
        top_n.sort(key=lambda x: x.index)

        return [s.text for s in top_n]


def tokenize_sentences(text: str) -> List[str]:
    """
    Tokenize text into sentences.

    Args:
        text: Input text to tokenize

    Returns:
        List of sentences
    """
    # Split on sentence boundaries while preserving quoted text
    sentence_endings = re.compile(r'(?<![A-Z][a-z]\.)(?<![A-Z]\.)(?<![0-9]\.)(?<![0-9])[.!?]"?'
                                 r'(?=\s+[A-Z]|$)')
    sentences = sentence_endings.split(text.strip())
    return [s.strip() for s in sentences if s.strip()]


def tokenize_words(text: str) -> List[str]:
    """
    Tokenize text into words.

    Args:
        text: Input text to tokenize

    Returns:
        List of normalized words
    """
    # Remove punctuation and normalize
    text = re.sub(r'[^\w\s]', '', text.lower())
    return text.split()


def _analyze_sentence(sentence: str, position: int, total_sentences: int) -> SentenceInfo:
    """
    Analyze a single sentence for scoring.

    Args:
        sentence: Sentence to analyze
        position: Position in text (0-indexed)
        total_sentences: Total number of sentences in text

    Returns:
        SentenceInfo object with analysis results
    """
    # Calculate position weight
    if position == 0:
        position_weight = 1.0
    elif position == total_sentences - 1:
        position_weight = 0.8
    else:
        position_weight = 1.0 / (position + 1)

    # Detect sentence types
    is_quote = bool(re.search(r'["“”].*["“”]', sentence))
    has_stats = bool(re.search(r'\d+', sentence))
    has_entities = bool(re.search(r'[A-Z][a-z]+\s[A-Z][a-z]+', sentence))

    # Calculate type bonuses
    type_bonus = 1.0
    if is_quote:
        type_bonus += 0.3
    if has_stats:
        type_bonus += 0.2
    if has_entities:
        type_bonus += 0.1

    # Calculate total score
    score = position_weight * type_bonus

    return SentenceInfo(
        index=position,
        text=sentence,
        position=position,
        is_quote=is_quote,
        has_stats=has_stats,
        has_entities=has_entities,
        score=score
    )


def position_based_summary(text: str, max_sentences: int = 3) -> str:
    """
    Position-aware summarization method.

    Weight sentences by position: title > first para > quotes > stats > last para
    Lead (first paragraph) is most important for news.

    Args:
        text: Text to summarize
        max_sentences: Maximum number of sentences to include

    Returns:
        Summarized text
    """
    sentences = tokenize_sentences(text)
    if len(sentences) <= max_sentences:
        return ' '.join(sentences)

    # Analyze and score sentences
    scored = []
    for i, sent in enumerate(sentences):
        info = _analyze_sentence(sent, i, len(sentences))
        scored.append(info)

    # Sort by score and take top N
    scored.sort(key=lambda x: x.score, reverse=True)
    top_n = scored[:max_sentences]

    # Sort by original position
    top_n.sort(key=lambda x: x.index)

    return ' '.join([s.text for s in top_n])


def textrank_summary(text: str, max_sentences: int = 3) -> str:
    """
    TextRank implementation for summarization.

    Tokenize into sentences, build similarity matrix (cosine similarity of TF-IDF vectors),
    apply PageRank algorithm, select top N sentences.

    Args:
        text: Text to summarize
        max_sentences: Maximum number of sentences to include

    Returns:
        Summarized text
    """
    sentences = tokenize_sentences(text)
    if len(sentences) <= max_sentences:
        return ' '.join(sentences)

    # Create TF-IDF vectorizer
    vectorizer = TfidfVectorizer(
        stop_words='english',
        tokenizer=tokenize_words,
        lowercase=True
    )

    # Compute TF-IDF matrix
    tfidf_matrix = vectorizer.fit_transform(sentences)

    # Compute cosine similarity matrix
    similarity_matrix = cosine_similarity(tfidf_matrix, tfidf_matrix)

    # Apply PageRank
    scores = _pagerank(similarity_matrix, damping=0.85, max_iter=100)

    # Select top N sentences
    scored_sentences = list(zip(range(len(sentences)), scores))
    scored_sentences.sort(key=lambda x: x[1], reverse=True)
    top_n_indices = [i for i, score in scored_sentences[:max_sentences]]

    # Sort by original position
    top_n_indices.sort()

    return ' '.join([sentences[i] for i in top_n_indices])


def _pagerank(matrix: np.ndarray, damping: float = 0.85, max_iter: int = 100,
              tol: float = 1e-6) -> np.ndarray:
    """
    Apply PageRank algorithm to a similarity matrix.

    Args:
        matrix: Similarity matrix
        damping: Damping factor
        max_iter: Maximum number of iterations
        tol: Convergence tolerance

    Returns:
        PageRank scores
    """
    n = matrix.shape[0]

    # Initialize scores
    scores = np.ones(n) / n

    for _ in range(max_iter):
        old_scores = scores.copy()

        # Compute new scores
        for i in range(n):
            # Sum of scores from other nodes
            sum_scores = 0.0
            for j in range(n):
                if i != j and matrix[j][i] > 0:
                    sum_scores += matrix[j][i] * scores[j] / np.sum(matrix[j])

            # Update score using damping factor
            scores[i] = (1 - damping) / n + damping * sum_scores

        # Check convergence
        if np.linalg.norm(scores - old_scores) < tol:
            break

    return scores


def lead_n_summary(text: str, n: int = 3) -> str:
    """
    Simple lead-N approach: extract first N sentences.

    Useful for fast/backup summarization.

    Args:
        text: Text to summarize
        n: Number of lead sentences to extract

    Returns:
        Summarized text
    """
    sentences = tokenize_sentences(text)
    return ' '.join(sentences[:min(n, len(sentences))])


def centroid_summary(cluster: Cluster, max_sentences: int = 3) -> str:
    """
    Centroid-based summarization for clusters.

    Compute centroid of cluster, find sentence closest to centroid.

    Args:
        cluster: Cluster to summarize
        max_sentences: Maximum number of sentences to include

    Returns:
        Summarized text
    """
    if not cluster.articles:
        return ""

    # If we have a representative article, use it
    if cluster.representative_article:
        return ArticleSummarizer().summarize(cluster.representative_article)

    # Otherwise, use the first article
    return ArticleSummarizer().summarize(cluster.articles[0])


def compute_sentence_scores(sentences: List[str]) -> Dict[int, float]:
    """
    Compute scores for each sentence.

    Args:
        sentences: List of sentences to score

    Returns:
        Dictionary mapping sentence index to score
    """
    scores = {}
    for i, sent in enumerate(sentences):
        info = _analyze_sentence(sent, i, len(sentences))
        scores[i] = info.score
    return scores


def normalize_scores(scores: Dict[int, float]) -> Dict[int, float]:
    """
    Normalize scores to 0-1 range.

    Args:
        scores: Dictionary of scores to normalize

    Returns:
        Normalized scores
    """
    if not scores:
        return {}

    min_score = min(scores.values())
    max_score = max(scores.values())

    if min_score == max_score:
        return {k: 1.0 for k in scores}

    normalized = {}
    for idx, score in scores.items():
        normalized[idx] = (score - min_score) / (max_score - min_score)

    return normalized
