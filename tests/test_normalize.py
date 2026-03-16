"""Tests for the normalize module."""

import pytest
from news_fetcher.normalize import (
    dedupe_articles,
    extract_published_date,
    normalize_article,
    normalize_text,
    normalize_title,
    normalize_url,
)
from news_fetcher.models import Article
from datetime import datetime


class TestNormalize:
    """Test class for the normalize module."""

    def test_normalize_text(self):
        """Test text normalization."""
        text = "  This is a  test  text.  \n\nWith  multiple   spaces.\n"
        normalized = normalize_text(text)
        assert normalized == "This is a test text. With multiple spaces."

    def test_normalize_title(self):
        """Test title normalization."""
        title = "  Test Article Title!  "
        normalized = normalize_title(title)
        assert normalized == "Test Article Title!"

    def test_normalize_url(self):
        """Test URL normalization."""
        url1 = "HTTP://EXAMPLE.COM/ARTICLE?param=1&param=2"
        url2 = "article.html"
        normalized1 = normalize_url(url1)
        normalized2 = normalize_url(url2)
        assert normalized1 == "http://example.com/article?param=1&param=2"
        assert normalized2 == "http://article.html"

    def test_extract_published_date(self):
        """Test published date extraction."""
        entry_with_date = {'published_parsed': (2025, 2, 25, 10, 30, 0)}
        entry_without_date = {}
        date1 = extract_published_date(entry_with_date)
        date2 = extract_published_date(entry_without_date)
        assert isinstance(date1, datetime)
        assert isinstance(date2, datetime)
        assert date1.year == 2025

    def test_dedupe_articles(self):
        """Test deduplication of articles."""
        article1 = Article(
            id="1",
            title="Test Article",
            content="Test content",
            url="https://example.com/article",
            source="example",
            published_at=datetime(2025, 2, 25)
        )

        article2 = Article(
            id="2",
            title="Test Article",
            content="Test content",
            url="https://example.com/article",
            source="example",
            published_at=datetime(2025, 2, 25)
        )

        deduplicated = dedupe_articles([article1, article2])
        assert len(deduplicated) == 1

    def test_normalize_article_preserves_acquisition_metadata(self):
        article = Article(
            id="1",
            title="  Test Article  ",
            content="<p>Test content</p>",
            url="HTTP://EXAMPLE.COM/ARTICLE",
            source="example",
            published_at=datetime(2025, 2, 25),
            candidate_strategy="frontpage",
            source_type="publisher_section",
            source_rank_position=4,
            source_section="top-stories",
            source_engagement_score=12.5,
            source_comment_count=18,
            source_view_count=200,
            source_like_count=25,
            source_curated_flag=True,
            source_official_flag=False,
            source_frontpage_timestamp=datetime(2025, 2, 25, 9, 30),
            acquisition_confidence=0.8,
        )

        normalized = normalize_article(article)

        assert normalized.title == "Test Article"
        assert normalized.content == "Test content"
        assert normalized.url == "http://example.com/article"
        assert normalized.candidate_strategy == "frontpage"
        assert normalized.source_type == "publisher_section"
        assert normalized.source_rank_position == 4
        assert normalized.source_section == "top-stories"
        assert normalized.source_engagement_score == 12.5
        assert normalized.source_comment_count == 18
        assert normalized.source_view_count == 200
        assert normalized.source_like_count == 25
        assert normalized.source_curated_flag is True
        assert normalized.source_official_flag is False
        assert normalized.source_frontpage_timestamp == datetime(2025, 2, 25, 9, 30)
        assert normalized.acquisition_confidence == 0.8
