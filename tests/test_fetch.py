"""Tests for the fetch module - fetching and parsing RSS feeds."""

from pathlib import Path

import pytest
import responses

from news_fetcher.fetch import fetch_all, fetch_html, fetch_rss
from news_fetcher.github_fetch import fetch_github_trending
from news_fetcher.normalize import normalize_article
from news_fetcher.models import Source


class TestFetch:
    """Test class for fetch module functionality."""

    def test_fetch_feeds_with_valid_feeds(
        self, mock_http_responses, sample_rss_feed, config_fixture
    ):
        for feed_url in config_fixture["feeds"]:
            mock_http_responses.add(
                responses.GET,
                feed_url,
                body=sample_rss_feed,
                status=200,
                content_type="application/rss+xml",
            )

        sources = [Source(name=f"Source {i}", url=url) for i, url in enumerate(config_fixture["feeds"])]
        results = fetch_all(sources)

        assert len(results) > 0
        assert all(isinstance(article, dict) or hasattr(article, "title") for article in results)

    def test_fetch_feeds_with_invalid_urls(self, mock_http_responses, config_fixture):
        invalid_urls = ["http://nonexistent.example.com/feed"]
        for url in invalid_urls:
            mock_http_responses.add(responses.GET, url, status=404)

        sources = [Source(name=f"Invalid Source {i}", url=url) for i, url in enumerate(invalid_urls)]
        results = fetch_all(sources)

        assert len(results) == 0

    def test_parse_rss_feed(self, mock_http_responses, sample_rss_feed):
        test_url = "https://example.com/feed.rss"
        mock_http_responses.add(
            responses.GET,
            test_url,
            body=sample_rss_feed,
            status=200,
            content_type="application/rss+xml",
        )

        items = fetch_rss(test_url)

        assert len(items) == 3
        assert all(hasattr(item, "title") and hasattr(item, "url") for item in items)

    def test_fetch_all_uses_configured_source_name(
        self, mock_http_responses, sample_rss_feed
    ):
        test_url = "https://example.com/feed.rss"
        mock_http_responses.add(
            responses.GET,
            test_url,
            body=sample_rss_feed,
            status=200,
            content_type="application/rss+xml",
        )

        results = fetch_all([Source(name="Configured Source", url=test_url)])

        assert len(results) == 3
        assert all(article.source == "Configured Source" for article in results)

    def test_fetch_html_extracts_articles(self, mock_http_responses):
        test_url = "https://example.com/news"
        html = """
<html>
  <body>
    <main>
      <article>
        <h2><a href="/story-1">Story One Headline</a></h2>
        <time datetime="2026-03-12T09:00:00Z"></time>
        <p>First story summary.</p>
      </article>
      <article>
        <h2><a href="https://example.com/story-2">Story Two Headline</a></h2>
        <p>Second story summary.</p>
      </article>
    </main>
  </body>
</html>
"""
        mock_http_responses.add(
            responses.GET,
            test_url,
            body=html,
            status=200,
            content_type="text/html",
        )

        results = fetch_html(test_url, source_name="HTML Source")

        assert len(results) == 2
        assert results[0].title == "Story One Headline"
        assert results[0].url == "https://example.com/story-1"
        assert results[0].source == "HTML Source"
        assert results[0].content == "First story summary."

    def test_fetch_all_uses_html_selector_from_config(self, mock_http_responses):
        test_url = "https://example.com/html-news"
        html = """
<html>
  <body>
    <main>
      <div class="story-card">
        <h2><a href="/picked-story">Picked Story Headline</a></h2>
        <p>Selected by CSS selector.</p>
      </div>
      <div class="ignored-card">
        <h2><a href="/ignored-story">Ignored Story Headline</a></h2>
        <p>Should not be returned.</p>
      </div>
    </main>
  </body>
</html>
"""
        mock_http_responses.add(
            responses.GET,
            test_url,
            body=html,
            status=200,
            content_type="text/html",
        )

        results = fetch_all(
            [
                Source(
                    name="HTML Source",
                    url=test_url,
                    type="html",
                    selector=".story-card",
                )
            ]
        )

        assert len(results) == 1
        assert results[0].title == "Picked Story Headline"
        assert results[0].source == "HTML Source"

    def test_fetch_all_preserves_source_acquisition_metadata(self, mock_http_responses):
        test_url = "https://example.com/html-frontpage"
        html = """
<html>
  <body>
    <main>
      <div class="story-card">
        <h2><a href="/picked-story">Picked Story Headline</a></h2>
        <p>Selected by CSS selector.</p>
      </div>
      <div class="story-card">
        <h2><a href="/second-story">Second Story Headline</a></h2>
        <p>Second card.</p>
      </div>
    </main>
  </body>
</html>
"""
        mock_http_responses.add(
            responses.GET,
            test_url,
            body=html,
            status=200,
            content_type="text/html",
        )

        results = fetch_all(
            [
                Source(
                    name="Editorial Source",
                    url=test_url,
                    type="html",
                    selector=".story-card",
                    source_type="curated_editorial",
                    candidate_strategy="curated",
                )
            ]
        )

        assert len(results) == 2
        assert results[0].candidate_strategy == "curated"
        assert results[0].source_type == "curated_editorial"
        assert results[0].source_rank_position == 1
        assert results[0].source_section == ".story-card"
        assert results[0].source_curated_flag is True
        assert results[0].source_official_flag is False

    def test_fetch_html_frontpage_fixture_preserves_visible_order_positions(
        self, mock_http_responses
    ):
        test_url = "https://example.com/frontpage"
        fixture_path = Path(__file__).parent / "fixtures" / "html_frontpage_ordered_sample.html"
        html = fixture_path.read_text(encoding="utf-8")
        mock_http_responses.add(
            responses.GET,
            test_url,
            body=html,
            status=200,
            content_type="text/html",
        )

        results = fetch_html(
            test_url,
            selector=".frontpage-list > li",
            source_name="Frontpage Source",
            source_config=Source(
                name="Frontpage Source",
                url=test_url,
                type="html",
                selector=".frontpage-list > li",
                source_type="generic_html",
                candidate_strategy="frontpage",
            ),
        )

        assert [article.title for article in results] == [
            "Lead Story Headline",
            "Second Story Headline",
            "Third Story Headline",
        ]
        assert [article.source_rank_position for article in results] == [1, 3, 4]
        assert all(article.candidate_strategy == "frontpage" for article in results)
        assert all(article.acquisition_confidence == 0.9 for article in results)

    def test_fetch_html_frontpage_falls_back_to_link_order_when_structure_is_unusable(
        self, mock_http_responses
    ):
        test_url = "https://example.com/frontpage-fallback"
        html = """
<html>
  <body>
    <main>
      <div class="story-card"><span>No usable headline link</span></div>
      <div class="story-card"><span>Still broken</span></div>
      <a href="/fallback-1">Fallback Story One</a>
      <a href="/fallback-2">Fallback Story Two</a>
    </main>
  </body>
</html>
"""
        mock_http_responses.add(
            responses.GET,
            test_url,
            body=html,
            status=200,
            content_type="text/html",
        )

        results = fetch_html(
            test_url,
            selector=".story-card",
            source_name="Frontpage Source",
            source_config=Source(
                name="Frontpage Source",
                url=test_url,
                type="html",
                selector=".story-card",
                source_type="generic_html",
                candidate_strategy="frontpage",
            ),
        )

        assert [article.title for article in results] == [
            "Fallback Story One",
            "Fallback Story Two",
        ]
        assert [article.source_rank_position for article in results] == [1, 2]
        assert all(article.acquisition_confidence == 0.4 for article in results)

    def test_frontpage_order_metadata_survives_normalization(self, mock_http_responses):
        test_url = "https://example.com/frontpage-normalized"
        fixture_path = Path(__file__).parent / "fixtures" / "html_frontpage_ordered_sample.html"
        html = fixture_path.read_text(encoding="utf-8")
        mock_http_responses.add(
            responses.GET,
            test_url,
            body=html,
            status=200,
            content_type="text/html",
        )

        fetched = fetch_html(
            test_url,
            selector=".frontpage-list > li",
            source_name="Frontpage Source",
            source_config=Source(
                name="Frontpage Source",
                url=test_url,
                type="html",
                selector=".frontpage-list > li",
                source_type="generic_html",
                candidate_strategy="frontpage",
            ),
        )
        normalized = [normalize_article(article) for article in fetched]

        assert [article.source_rank_position for article in normalized] == [1, 3, 4]
        assert all(article.candidate_strategy == "frontpage" for article in normalized)

    def test_parse_invalid_rss_feed(self, mock_http_responses):
        test_url = "https://example.com/invalid.rss"
        invalid_xml = "<invalid><rss>content</rss></invalid>"
        mock_http_responses.add(
            responses.GET,
            test_url,
            body=invalid_xml,
            status=200,
            content_type="application/rss+xml",
        )

        articles = fetch_rss(test_url)

        assert len(articles) == 0

    def test_fetch_with_timeout(self):
        test_url = "https://nonexistent.example.com/feed.rss"

        with pytest.raises(Exception):
            fetch_rss(test_url, timeout=0.001)


    def test_fetch_github_trending_fixture_extracts_project_candidates(self, mock_http_responses):
        test_url = "https://github.com/trending"
        fixture_path = Path(__file__).parent / "fixtures" / "github_trending_sample.html"
        html = fixture_path.read_text(encoding="utf-8")
        mock_http_responses.add(
            responses.GET,
            test_url,
            body=html,
            status=200,
            content_type="text/html",
        )

        results = fetch_github_trending(
            test_url,
            source_config=Source(
                name="GitHub Trending",
                url=test_url,
                type="html",
                source_type="github_project_discovery",
                candidate_strategy="project_discovery",
            ),
        )

        assert results
        assert all(article.item_type == "github_project" for article in results)
        assert all(article.source_type == "github_project_discovery" for article in results)
        assert all(article.candidate_strategy == "project_discovery" for article in results)
        assert results[0].source_rank_position == 1
        assert results[0].item_metadata["repo_full_name"]
        assert results[0].item_metadata["repo_url"].startswith("https://github.com/")
        assert results[0].item_metadata["source_surface"] == "trending"

    def test_fetch_all_routes_github_project_discovery_sources(self, mock_http_responses):
        test_url = "https://github.com/trending"
        fixture_path = Path(__file__).parent / "fixtures" / "github_trending_sample.html"
        html = fixture_path.read_text(encoding="utf-8")
        mock_http_responses.add(
            responses.GET,
            test_url,
            body=html,
            status=200,
            content_type="text/html",
        )

        results = fetch_all(
            [
                Source(
                    name="GitHub Trending",
                    url=test_url,
                    type="html",
                    source_type="github_project_discovery",
                    candidate_strategy="project_discovery",
                )
            ]
        )

        assert results
        assert results[0].item_type == "github_project"
        assert results[0].source == "GitHub Trending"
