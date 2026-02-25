"""
Tests for the fetch module - fetching and parsing RSS feeds.
"""

import pytest
import responses
from news_fetcher.fetch import fetch_rss, fetch_html, fetch_all, should_fetch
from news_fetcher.models import Source


class TestFetch:
    """Test class for fetch module functionality."""

    def test_fetch_feeds_with_valid_feeds(self, mock_http_responses, sample_rss_feed, config_fixture):
        """Test fetching feeds with valid URLs and responses."""
        # Arrange
        for feed_url in config_fixture["feeds"]:
            mock_http_responses.add(
                responses.GET,
                feed_url,
                body=sample_rss_feed,
                status=200,
                content_type="application/rss+xml"
            )

        sources = [Source(name=f"Source {i}", url=url) for i, url in enumerate(config_fixture["feeds"])]

        # Act
        results = fetch_all(sources)

        # Assert
        assert len(results) > 0
        assert all(isinstance(article, dict) or hasattr(article, "title") for article in results)

    def test_fetch_feeds_with_invalid_urls(self, mock_http_responses, config_fixture):
        """Test fetching feeds with invalid URLs."""
        # Arrange
        invalid_urls = ["http://nonexistent.example.com/feed"]
        for url in invalid_urls:
            mock_http_responses.add(
                responses.GET,
                url,
                status=404
            )

        sources = [Source(name=f"Invalid Source {i}", url=url) for i, url in enumerate(invalid_urls)]

        # Act
        results = fetch_all(sources)

        # Assert
        assert len(results) == 0

    def test_parse_rss_feed(self, mock_http_responses, sample_rss_feed):
        """Test parsing of RSS feed content."""
        # Arrange
        test_url = "https://example.com/feed.rss"
        mock_http_responses.add(
            responses.GET,
            test_url,
            body=sample_rss_feed,
            status=200,
            content_type="application/rss+xml"
        )

        # Act
        items = fetch_rss(test_url)

        # Assert
        assert len(items) == 3
        assert all(hasattr(item, "title") and hasattr(item, "url") for item in items)

    def test_parse_invalid_rss_feed(self, mock_http_responses):
        """Test parsing invalid RSS feed content."""
        # Arrange
        test_url = "https://example.com/invalid.rss"
        invalid_xml = "<invalid><rss>content</rss></invalid>"
        mock_http_responses.add(
            responses.GET,
            test_url,
            body=invalid_xml,
            status=200,
            content_type="application/rss+xml"
        )

        # Act
        articles = fetch_rss(test_url)

        # Assert
        assert len(articles) == 0

    def test_fetch_with_timeout(self):
        """Test fetching feeds with timeout scenario."""
        # Arrange
        test_url = "https://nonexistent.example.com/feed.rss"

        # Act
        with pytest.raises(Exception):
            fetch_rss(test_url, timeout=0.001)