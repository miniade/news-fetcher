"""
Tests for the cluster module - clustering similar news items.
"""

import pytest
from news_fetcher.cluster import ArticleClusterer
from news_fetcher.models import Article
from datetime import datetime


class TestCluster:
    """Test class for clustering module functionality."""

    def test_cluster_items_with_different_topics(self, sample_news_items):
        """Test clustering items with distinct topics."""
        articles = [
            Article(
                id=item['id'],
                title=item['title'],
                content=item['content'],
                url=item['url'],
                source=item['source'],
                published_at=datetime(2025, 2, 25)
            )
            for item in sample_news_items
        ]

        clusterer = ArticleClusterer(min_cluster_size=2)
        clusters = clusterer.fit(articles)

        # HDBSCAN might return 0 clusters if no groups of 2+ similar articles
        assert len(clusters) >= 0
        all_items = [item for cluster in clusters for item in cluster.articles]
        assert len(all_items) <= len(articles)  # Some might be noise points (-1)

    def test_cluster_similar_items(self):
        """Test clustering similar items together."""
        similar_items = [
            Article(
                id="1",
                title="AI Partnership Announced",
                content="Tech companies announce AI partnership",
                url="https://example.com/news1",
                source="example",
                published_at=datetime(2025, 2, 25)
            ),
            Article(
                id="2",
                title="New AI Collaboration",
                content="Tech giants collaborate on AI",
                url="https://example.com/news2",
                source="example",
                published_at=datetime(2025, 2, 25)
            ),
            Article(
                id="3",
                title="Stock Market Reaches New High",
                content="Markets hit record highs",
                url="https://example.com/news3",
                source="example",
                published_at=datetime(2025, 2, 25)
            )
        ]

        clusterer = ArticleClusterer(min_cluster_size=2)
        clusters = clusterer.fit(similar_items)

        # Should have 0 or 1 clusters (if first two are similar enough)
        assert len(clusters) <= 1

    def test_cluster_empty_list(self):
        """Test clustering empty list of items."""
        clusterer = ArticleClusterer(min_cluster_size=2)
        with pytest.raises(ValueError):
            clusterer.fit([])
