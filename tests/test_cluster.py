"""
Tests for the cluster module - clustering similar news items.
"""

import pytest
from src.cluster import cluster_news_items


class TestCluster:
    """Test class for clustering module functionality."""

    def test_cluster_items_with_different_topics(self, sample_news_items):
        """Test clustering items with distinct topics."""
        # Act
        clusters = cluster_news_items(sample_news_items)

        # Assert
        assert len(clusters) >= 1
        all_items = [item for cluster in clusters for item in cluster]
        assert len(all_items) == len(sample_news_items)

    def test_cluster_similar_items(self):
        """Test clustering similar items together."""
        # Arrange
        similar_items = [
            {
                "id": "1",
                "title": "AI Partnership Announced",
                "content": "Tech companies announce AI partnership",
                "keywords": ["ai", "partnership"]
            },
            {
                "id": "2",
                "title": "New AI Collaboration",
                "content": "Tech giants collaborate on AI",
                "keywords": ["ai", "partnership"]
            },
            {
                "id": "3",
                "title": "Stock Market Reaches New High",
                "content": "Markets hit record highs",
                "keywords": ["markets", "finance"]
            }
        ]

        # Act
        clusters = cluster_news_items(similar_items)

        # Assert
        assert len(clusters) == 2
        assert any(len(cluster) == 2 for cluster in clusters)
        assert any(len(cluster) == 1 for cluster in clusters)

    def test_cluster_empty_list(self):
        """Test clustering empty list of items."""
        # Act
        clusters = cluster_news_items([])

        # Assert
        assert len(clusters) == 0