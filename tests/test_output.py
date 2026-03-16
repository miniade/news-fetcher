"""Tests for the output module."""

import json
from datetime import datetime

from news_fetcher.models import Article
from news_fetcher.output import OutputFormatter


class TestOutput:
    """Test class for the output module."""

    def _sample_articles(self):
        return [
            Article(
                id="1",
                title="Test Article 1",
                content="Test content 1",
                url="https://example.com/news1",
                source="Example News",
                published_at=datetime(2025, 2, 25),
                fetched_at=datetime(2025, 2, 25),
                summary="Summary 1",
                score=0.9,
                embeddings=[0.1, 0.2, 0.3],
                candidate_strategy="frontpage",
                source_type="platform_feed",
                source_rank_position=2,
                source_section="homepage",
                source_engagement_score=91.5,
                source_comment_count=14,
                source_view_count=500,
                source_like_count=42,
                source_curated_flag=False,
                source_official_flag=True,
                source_frontpage_timestamp=datetime(2025, 2, 25, 12, 0),
                acquisition_confidence=0.7,
            )
        ]

    def test_format_json(self):
        formatter = OutputFormatter(output_format="json")
        output = formatter.format(self._sample_articles())
        parsed = json.loads(output)
        assert parsed["articles"][0]["title"] == "Test Article 1"
        assert parsed["articles"][0]["score"] == 0.9
        assert parsed["articles"][0]["candidate_strategy"] == "frontpage"
        assert parsed["articles"][0]["source_type"] == "platform_feed"
        assert parsed["articles"][0]["source_rank_position"] == 2
        assert parsed["articles"][0]["source_frontpage_timestamp"] == "2025-02-25T12:00:00"
        assert "embeddings" not in parsed["articles"][0]

    def test_format_markdown(self):
        formatter = OutputFormatter(output_format="markdown")
        output = formatter.format(self._sample_articles())
        assert "Test Article 1" in output
        assert "Summary 1" in output

    def test_format_csv(self):
        formatter = OutputFormatter(output_format="csv")
        output = formatter.format(self._sample_articles())
        assert "Test Article 1" in output
        assert "score" in output

    def test_format_rss(self):
        formatter = OutputFormatter(output_format="rss")
        output = formatter.format(self._sample_articles())
        assert "<title>Test Article 1</title>" in output

    def test_save_to_file(self, tmp_path):
        formatter = OutputFormatter(output_format="json")
        output_path = tmp_path / "nested" / "news.json"
        formatter.save(self._sample_articles(), str(output_path))

        assert output_path.exists()
        parsed = json.loads(output_path.read_text(encoding="utf-8"))
        assert parsed["articles"][0]["title"] == "Test Article 1"
        assert "embeddings" not in parsed["articles"][0]
