"""
End-to-end tests for the news-fetcher pipeline.
"""

import pytest
import responses
from src.main import run_pipeline


class TestEndToEnd:
    """Test class for end-to-end pipeline testing."""

    @pytest.mark.slow
    def test_full_pipeline_run(self, mock_http_responses, sample_rss_feed, sample_html_news_page):
        """Test a full pipeline run from start to finish."""
        # Arrange
        feed_url = "https://example.com/test-feed.rss"
        article_url = "https://example.com/test-article"

        mock_http_responses.add(
            responses.GET,
            feed_url,
            body=sample_rss_feed,
            status=200,
            content_type="application/rss+xml"
        )

        mock_http_responses.add(
            responses.GET,
            article_url,
            body=sample_html_news_page,
            status=200,
            content_type="text/html"
        )

        # Act
        results = run_pipeline({
            "feeds": [feed_url],
            "fetch": {"timeout": 10, "retries": 3},
            "normalize": {"min_length": 50, "max_length": 5000},
            "dedup": {"threshold": 0.85},
            "cluster": {"threshold": 0.7},
            "rank": {"algorithm": "tfidf"},
            "diversify": {"max_per_topic": 3},
            "summarize": {"model": "default"},
            "output": {"formats": ["json"], "directory": "test_output"}
        })

        # Assert
        assert results is not None
        assert "success" in results
        assert results["success"]
        assert "statistics" in results

    def test_pipeline_with_error_handling(self, mock_http_responses):
        """Test pipeline handles errors gracefully."""
        # Arrange
        feed_url = "https://example.com/invalid-feed.rss"

        mock_http_responses.add(
            responses.GET,
            feed_url,
            status=404
        )

        # Act
        results = run_pipeline({
            "feeds": [feed_url],
            "fetch": {"timeout": 10, "retries": 1},
            "output": {"formats": ["json"], "directory": "test_output"}
        })

        # Assert
        assert results is not None
        assert "success" in results
        assert not results["success"]