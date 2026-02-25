"""
Tests for the fetch module - fetching and parsing RSS feeds.
"""

import pytest
import responses
from news_fetcher.fetch import fetch_rss, fetch_html, fetch_all, should_fetch


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

        # Act
        results = fetch_feeds(config_fixture["feeds"])

        # Assert
        assert len(results) == len(config_fixture["feeds"])
        for feed_url, (status, data) in results.items():
            assert status == 200
            assert data is not None
            assert len(data) > 0

    def test_fetch_feeds_with_invalid_urls(self, mock_http_responses, config_fixture):
        """Test fetching feeds with invalid URLs."""
        # Arrange
        invalid_urls = ["invalid-url", "http://nonexistent.example.com/feed"]
        for url in invalid_urls:
            mock_http_responses.add(
                responses.GET,
                url,
                status=404
            )

        # Act
        results = fetch_feeds(invalid_urls)

        # Assert
        for url, (status, data) in results.items():
            assert status != 200
            assert data is None

    def test_parse_rss_feed(self, sample_rss_feed):
        """Test parsing of RSS feed content."""
        # Act
        items = parse_rss_feed(sample_rss_feed)

        # Assert
        assert len(items) == 3
        assert all("title" in item and "link" in item for item in items)

    def test_parse_invalid_rss_feed(self):
        """Test parsing invalid RSS feed content."""
        # Arrange
        invalid_xml = "<invalid><rss>content</rss></invalid>"

        # Act & Assert
        with pytest.raises(Exception):
            parse_rss_feed(invalid_xml)

    def test_fetch_with_timeout(self, mock_http_responses, config_fixture):
        """Test fetching feeds with timeout scenario."""
        # Arrange
        for feed_url in config_fixture["feeds"]:
            mock_http_responses.add(
                responses.GET,
                feed_url,
                body=responses.ResponsesTemplate(timeout=1),
                status=200
            )

        # Act
        results = fetch_feeds(config_fixture["feeds"], timeout=0.1)

        # Assert
        for feed_url, (status, data) in results.items():
            assert status == -1
            assert data is None