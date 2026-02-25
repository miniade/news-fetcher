"""
Tests for the normalize module - normalizing news content.
"""

import pytest
from news_fetcher.normalize import normalize_article, normalize_text, normalize_title, normalize_url, extract_published_date, dedupe_articles


class TestNormalize:
    """Test class for normalization module functionality."""

    def test_normalize_valid_html(self, sample_html_news_page):
        """Test normalization of valid HTML content."""
        # Arrange
        raw_item = {
            "title": "Test Article",
            "url": "https://example.com/article",
            "content": sample_html_news_page,
            "published_at": "2025-02-25"
        }

        # Act
        normalized_item = normalize_news_item(raw_item)

        # Assert
        assert normalized_item["title"] == "Test Article"
        assert normalized_item["url"] == "https://example.com/article"
        assert normalized_item["content"] is not None
        assert len(normalized_item["content"]) > 0
        assert "Test Article" in normalized_item["title"]
        assert "artificial intelligence" in normalized_item["content"].lower()

    def test_normalize_empty_content(self):
        """Test normalization of item with empty content."""
        # Arrange
        raw_item = {
            "title": "Empty Content Article",
            "url": "https://example.com/empty",
            "content": "",
            "published_at": "2025-02-25"
        }

        # Act & Assert
        with pytest.raises(ValueError):
            normalize_news_item(raw_item)

    def test_normalize_content_too_short(self):
        """Test normalization of content that's too short."""
        # Arrange
        raw_item = {
            "title": "Short Article",
            "url": "https://example.com/short",
            "content": "<p>Too short</p>",
            "published_at": "2025-02-25"
        }

        # Act & Assert
        with pytest.raises(ValueError):
            normalize_news_item(raw_item, min_length=50)

    def test_normalize_invalid_date(self):
        """Test normalization with invalid published date."""
        # Arrange
        raw_item = {
            "title": "Invalid Date Article",
            "url": "https://example.com/invalid-date",
            "content": "<p>Valid content but invalid date</p>",
            "published_at": "invalid-date"
        }

        # Act
        normalized_item = normalize_news_item(raw_item)

        # Assert
        assert normalized_item["published_at"] is None

    def test_normalize_content_with_images(self):
        """Test normalization of content with images."""
        # Arrange
        html_with_images = """<p>Content with <img src="image.jpg" alt="test image"> images</p>"""
        raw_item = {
            "title": "Article with Images",
            "url": "https://example.com/images",
            "content": html_with_images,
            "published_at": "2025-02-25"
        }

        # Act
        normalized_item = normalize_news_item(raw_item)

        # Assert
        assert normalized_item["content"] == "Content with images"