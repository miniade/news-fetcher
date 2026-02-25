"""
Tests for the diversify module - diversifying news content.
"""

import pytest
from src.diversify import diversify_news_items


class TestDiversify:
    """Test class for diversification module functionality."""

    def test_diversify_items_with_no_duplicate_topics(self, sample_news_items):
        """Test diversification when there are no duplicate topics."""
        # Act
        diversified = diversify_news_items(sample_news_items)

        # Assert
        assert len(diversified) == len(sample_news_items)

    def test_diversify_items_with_duplicate_topics(self):
        """Test diversification limits per topic."""
        # Arrange
        items_with_same_topic = [
            {
                "id": f"item-{i}",
                "title": f"AI News {i}",
                "content": f"Content about AI {i}",
                "keywords": ["ai", "technology"],
                "topic": "ai"
            }
            for i in range(5)
        ]

        # Act
        diversified = diversify_news_items(items_with_same_topic, max_per_topic=3)

        # Assert
        assert len(diversified) == 3

    def test_diversify_with_multiple_topics(self):
        """Test diversification across multiple topics."""
        # Arrange
        items = [
            {"id": "1", "title": "AI News", "topic": "ai"},
            {"id": "2", "title": "Market Update", "topic": "finance"},
            {"id": "3", "title": "Climate News", "topic": "environment"},
            {"id": "4", "title": "Tech Trends", "topic": "technology"},
            {"id": "5", "title": "AI Research", "topic": "ai"},
            {"id": "6", "title": "Stock Analysis", "topic": "finance"}
        ]

        # Act
        diversified = diversify_news_items(items, max_per_topic=2)

        # Assert
        topic_counts = {}
        for item in diversified:
            topic_counts[item["topic"]] = topic_counts.get(item["topic"], 0) + 1

        assert all(count <= 2 for count in topic_counts.values())