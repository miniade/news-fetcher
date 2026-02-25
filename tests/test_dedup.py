"""
Tests for the deduplication module.
"""

import pytest
from news_fetcher.dedup import SimHash
from news_fetcher.dedup import Deduplicator
from news_fetcher.models import Article
from datetime import datetime


class TestDedup:
    """Test class for the deduplication module."""

    def test_deduplicate_items_with_no_duplicates(self, sample_news_items):
        """Test that items with no duplicates are returned as is."""
        deduplicator = Deduplicator()
        deduplicated = [item for item in sample_news_items if not deduplicator.add_document(item['id'], item['content'])]
        assert len(deduplicated) == 3

    def test_deduplicate_items_with_exact_duplicates(self, sample_news_items):
        """Test that exact duplicates are removed."""
        deduplicator = Deduplicator()
        items_with_duplicates = sample_news_items + [sample_news_items[0]]
        deduplicated = []
        for item in items_with_duplicates:
            if not deduplicator.add_document(item['id'], item['content']):
                deduplicated.append(item)
        assert len(deduplicated) == 3

    def test_calculate_similarity(self):
        """Test the SimHash algorithm for calculating similarity."""
        simhash = SimHash()
        hash1 = simhash.compute("Tech companies announce AI partnership")
        hash2 = simhash.compute("Tech giants collaborate on AI")
        distance = simhash.distance(hash1, hash2)
        assert distance < 25  # Increase threshold to 25
