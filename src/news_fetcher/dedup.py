"""
Deduplication module for news-fetcher application.

This module provides functionality for detecting and removing duplicate
and near-duplicate news articles using SimHash algorithm.
"""

import hashlib
import re
from collections import Counter
from typing import Dict, List, Optional, Set, Tuple


class SimHash:
    """
    SimHash implementation for near-duplicate detection.

    SimHash creates a compact fingerprint for text that can be used to
    efficiently detect near-duplicates using Hamming distance.

    Attributes:
        hashbits: Number of bits in the hash (default: 64)
    """

    def __init__(self, hashbits: int = 64) -> None:
        """
        Initialize SimHash with specified hash bit size.

        Args:
            hashbits: Number of bits in the hash (default: 64)
        """
        self.hashbits = hashbits

    def _tokenize(self, text: str) -> List[Tuple[str, int]]:
        """
        Tokenize text with TF-IDF-like weights.

        Args:
            text: Input text to tokenize

        Returns:
            List of (token, weight) tuples
        """
        # Simple tokenization
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        word_counts = Counter(words)

        # Calculate TF-like weights
        total_words = len(words)
        if total_words == 0:
            return []

        tokens = []
        for word, count in word_counts.items():
            # Simple TF weight
            weight = count / total_words
            tokens.append((word, weight))

        return tokens

    def _compute_hash(self, token: str) -> int:
        """
        Compute hash for a token using MD5.

        Args:
            token: Input token

        Returns:
            Hash value as integer
        """
        md5 = hashlib.md5(token.encode('utf-8'))
        return int(md5.hexdigest(), 16)

    def compute(self, text: str) -> int:
        """
        Compute SimHash fingerprint for text.

        Args:
            text: Input text

        Returns:
            SimHash fingerprint as integer
        """
        if not text:
            return 0

        # Tokenize with weights
        tokens = self._tokenize(text)

        if not tokens:
            return 0

        # Initialize vector
        v = [0.0] * self.hashbits

        # Accumulate weighted hashes
        for token, weight in tokens:
            hash_value = self._compute_hash(token)
            for i in range(self.hashbits):
                bit = (hash_value >> i) & 1
                if bit == 1:
                    v[i] += weight
                else:
                    v[i] -= weight

        # Generate fingerprint
        fingerprint = 0
        for i in range(self.hashbits):
            if v[i] > 0:
                fingerprint |= (1 << i)

        return fingerprint

    def distance(self, hash1: int, hash2: int) -> int:
        """
        Compute Hamming distance between two SimHash fingerprints.

        Args:
            hash1: First hash value
            hash2: Second hash value

        Returns:
            Hamming distance (number of differing bits)
        """
        x = hash1 ^ hash2
        distance = 0
        while x:
            distance += 1
            x &= x - 1
        return distance


class Deduplicator:
    """
    Main deduplication interface using SimHash.

    This class provides high-level deduplication functionality for
    identifying and removing duplicate or near-duplicate articles.

    Attributes:
        threshold: Hamming distance threshold for duplicates (default: 3)
        hashbits: Number of bits in SimHash (default: 64)
    """

    def __init__(self, threshold: int = 3, hashbits: int = 64) -> None:
        """
        Initialize the deduplicator.

        Args:
            threshold: Hamming distance threshold for duplicates (default: 3)
            hashbits: Number of bits in SimHash (default: 64)
        """
        self.threshold = threshold
        self.hashbits = hashbits
        self.simhash = SimHash(hashbits=hashbits)
        self._fingerprints: Dict[str, int] = {}

    def is_duplicate(self, hash1: int, hash2: int) -> bool:
        """
        Check if two hashes are duplicates based on threshold.

        Args:
            hash1: First hash value
            hash2: Second hash value

        Returns:
            True if Hamming distance <= threshold, False otherwise
        """
        distance = self.simhash.distance(hash1, hash2)
        return distance <= self.threshold

    def find_duplicates(self, hashes: List[Tuple[str, int]]) -> List[List[str]]:
        """
        Find all duplicate groups in a list of hashes.

        Args:
            hashes: List of (doc_id, hash_value) tuples

        Returns:
            List of duplicate groups (each group is a list of doc_ids)
        """
        n = len(hashes)
        visited = [False] * n
        groups = []

        for i in range(n):
            if visited[i]:
                continue

            group = [hashes[i][0]]
            visited[i] = True

            for j in range(i + 1, n):
                if visited[j]:
                    continue

                if self.is_duplicate(hashes[i][1], hashes[j][1]):
                    group.append(hashes[j][0])
                    visited[j] = True

            if len(group) > 1:
                groups.append(group)

        return groups

    def add_document(self, doc_id: str, text: str) -> Optional[str]:
        """
        Add a document and check for duplicates.

        Args:
            doc_id: Unique document identifier
            text: Document text content

        Returns:
            ID of duplicate document if found, None otherwise
        """
        fingerprint = self.simhash.compute(text)

        # Check against existing fingerprints
        for existing_id, existing_hash in self._fingerprints.items():
            if self.is_duplicate(fingerprint, existing_hash):
                return existing_id

        # Add to fingerprints
        self._fingerprints[doc_id] = fingerprint
        return None

    def get_fingerprint(self, doc_id: str) -> Optional[int]:
        """
        Get fingerprint for a document.

        Args:
            doc_id: Document identifier

        Returns:
            Fingerprint value if found, None otherwise
        """
        return self._fingerprints.get(doc_id)

    def clear(self) -> None:
        """Clear all stored fingerprints."""
        self._fingerprints.clear()


def compute_shingles(text: str, k: int = 3) -> Set[str]:
    """
    Compute k-gram shingles for text.

    Args:
        text: Input text
        k: Shingle size (default: 3)

    Returns:
        Set of k-gram shingles
    """
    words = text.lower().split()
    if len(words) < k:
        return set(words)

    shingles = set()
    for i in range(len(words) - k + 1):
        shingle = ' '.join(words[i:i + k])
        shingles.add(shingle)

    return shingles


def jaccard_similarity(set1: Set, set2: Set) -> float:
    """
    Compute Jaccard similarity between two sets.

    Args:
        set1: First set
        set2: Second set

    Returns:
        Jaccard similarity (0.0 to 1.0)
    """
    if not set1 and not set2:
        return 1.0
    if not set1 or not set2:
        return 0.0

    intersection = len(set1 & set2)
    union = len(set1 | set2)

    return intersection / union if union > 0 else 0.0
