"""
Tests for the dedup module - detecting and removing duplicates.
"""

import pytest
from src.dedup import deduplicate_items, calculate_similarity


class TestDedup:
    """Test class for deduplication module functionality."""

    def test_deduplicate_items_with_no_duplicates(self, sample_news_items):
        """Test deduplication when there are no duplicates."""
        # Act
        deduplicated = deduplicate_items(sample_news_items)

        # Assert
        assert len(deduplicated) == len(sample_news_items)

    def test_deduplicate_items_with_exact_duplicates(self, sample_news_items):
        """Test deduplication of exact duplicates."""
        # Arrange
        items_with_duplicates = sample_news_items + [sample_news_items[0]]

        # Act
        deduplicated = deduplicate_items(items_with_duplicates)

        # Assert
        assert len(deduplicated) == len(sample_news_items)

    def test_deduplicate_items_with_similar_content(self):
        """Test deduplication of similar content items."""
        # Arrange
        similar_items = [
            {
                "id": "1",
                "title": "Tech Giants Announce New AI Partnership",
                "content": "Leading tech companies announce AI partnership",
                "url": "https://example.com/news1",
                "source": "Source1",
                "published_at": "2025-02-25",
                "author": "Author1",
                "language": "en",
                "keywords": ["ai", "partnership"]
            },
            {
                "id": "2",
                "title": "New AI Partnership Announced by Tech Giants",
                "content": "Tech companies announce new AI partnership",
                "url": "https://example.com/news2",
                "source": "Source2",
                "published_at": "2025-02-25",
                "author": "Author2",
                "language": "en",
                "keywords": ["ai", "partnership"]
            }
        ]

        # Act
        deduplicated = deduplicate_items(similar_items, threshold=0.5)

        # Assert
        assert len(deduplicated) == 1

    def test_calculate_similarity(self):
        """Test similarity calculation between two items."""
        # Arrange
        item1 = {
            "title": "Tech Giants Announce AI Partnership",
            "content": "Leading technology companies announce AI partnership"
        }
        item2 = {
            "title": "Tech Companies Announce AI Collaboration",
            "content": "Major tech companies announce artificial intelligence collaboration"
        }

        # Act
        title_sim = calculate_similarity(item1["title"], item2["title"])
        content_sim = calculate_similarity(item1["content"], item2["content"])

        # Assert
        assert 0.5 < title_sim < 1.0
        assert 0.5 < content_sim < 1.0