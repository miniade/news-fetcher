"""
Tests for the rank module - ranking news items.
"""

import pytest
from src.rank import rank_news_items


class TestRank:
    """Test class for ranking module functionality."""

    def test_rank_items_by_relevance(self, sample_news_items):
        """Test ranking items by relevance."""
        # Act
        ranked = rank_news_items(sample_news_items)

        # Assert
        assert len(ranked) == len(sample_news_items)
        assert isinstance(ranked, list)

    def test_rank_empty_list(self):
        """Test ranking empty list of items."""
        # Act
        ranked = rank_news_items([])

        # Assert
        assert ranked == []

    def test_rank_with_query(self):
        """Test ranking items with query-based relevance."""
        # Arrange
        items = [
            {
                "id": "1",
                "title": "AI Partnership Announced",
                "content": "Tech companies announce AI partnership",
                "keywords": ["ai", "partnership"]
            },
            {
                "id": "2",
                "title": "Stock Market Reaches New High",
                "content": "Markets hit record highs",
                "keywords": ["markets", "finance"]
            },
            {
                "id": "3",
                "title": "AI Research Advances",
                "content": "New AI research breakthrough",
                "keywords": ["ai", "research"]
            }
        ]

        # Act
        ranked = rank_news_items(items, query="artificial intelligence")

        # Assert
        assert len(ranked) == 3
        assert ranked[0]["id"] in ["1", "3"]