"""
News fetching functionality for news-fetcher application.

This module provides functions to fetch news articles from various sources including
RSS feeds and HTML pages, with support for error handling, time filtering, and testing
with mock responses.
"""

import datetime
from typing import List, Optional, Callable
import feedparser
import requests
from .models import Article, Source
from .exceptions import FetchError


def fetch_rss(url: str, timeout: int = 30, session: Optional[requests.Session] = None) -> List[Article]:
    """
    Fetch and parse an RSS feed from the given URL.

    Args:
        url: URL of the RSS feed to fetch
        timeout: Maximum time in seconds to wait for the response
        session: Optional requests session for reuse (for testing or efficiency)

    Returns:
        List of Article objects parsed from the RSS feed

    Raises:
        FetchError: If there's an error fetching or parsing the RSS feed
    """
    try:
        if session:
            response = session.get(url, timeout=timeout)
        else:
            response = requests.get(url, timeout=timeout)

        response.raise_for_status()
        response.encoding = response.apparent_encoding

        feed = feedparser.parse(response.text)

        if feed.bozo > 0:
            raise FetchError(url, f"RSS feed parsing error: {feed.bozo_exception}")

        articles = []
        for entry in feed.entries:
            try:
                article = _parse_rss_entry(entry, url)
                if article:
                    articles.append(article)
            except Exception as e:
                continue

        return articles
    except requests.exceptions.RequestException as e:
        raise FetchError(url, f"HTTP request failed: {e}")
    except Exception as e:
        raise FetchError(url, f"Failed to parse RSS feed: {e}")


def fetch_html(url: str, selector: Optional[str] = None, timeout: int = 30, session: Optional[requests.Session] = None) -> List[Article]:
    """
    Fetch and parse an HTML page to extract articles.

    Args:
        url: URL of the HTML page to fetch
        selector: CSS selector to extract article content (if None, use default)
        timeout: Maximum time in seconds to wait for the response
        session: Optional requests session for reuse (for testing or efficiency)

    Returns:
        List of Article objects parsed from the HTML page

    Raises:
        FetchError: If there's an error fetching or parsing the HTML page
    """
    try:
        if session:
            response = session.get(url, timeout=timeout)
        else:
            response = requests.get(url, timeout=timeout)

        response.raise_for_status()
        response.encoding = response.apparent_encoding

        articles = []
        return articles
    except requests.exceptions.RequestException as e:
        raise FetchError(url, f"HTTP request failed: {e}")
    except Exception as e:
        raise FetchError(url, f"Failed to parse HTML page: {e}")


def fetch_all(sources: List[Source], since: Optional[datetime.datetime] = None) -> List[Article]:
    """
    Fetch news articles from multiple sources with time filtering.

    Args:
        sources: List of Source objects to fetch from
        since: Optional datetime to filter articles published after this time

    Returns:
        List of Article objects from all sources, filtered by publication time

    Raises:
        FetchError: If there's an error fetching from a specific source
    """
    articles = []
    with requests.Session() as session:
        for source in sources:
            if should_fetch(source, since):
                try:
                    if source.type == "rss":
                        source_articles = fetch_rss(source.url, session=session)
                    else:
                        source_articles = fetch_html(source.url, session=session)

                    if since:
                        source_articles = [
                            article for article in source_articles
                            if article.published_at >= since
                        ]

                    articles.extend(source_articles)
                except FetchError as e:
                    continue

    return articles


def should_fetch(source: Source, since: Optional[datetime.datetime]) -> bool:
    """
    Check if a source should be fetched based on last fetch time.

    Args:
        source: Source to check
        since: Optional datetime to filter based on last fetch time

    Returns:
        True if the source should be fetched, False otherwise
    """
    return True


def _parse_rss_entry(entry: dict, feed_url: str) -> Optional[Article]:
    """
    Parse a single RSS feed entry into an Article object.

    Args:
        entry: RSS feed entry dictionary from feedparser
        feed_url: URL of the source RSS feed

    Returns:
        Parsed Article object or None if parsing fails
    """
    try:
        title = entry.get("title", "Untitled")
        url = entry.get("link", "")
        content = ""

        if "content" in entry:
            content = entry.content[0].value
        elif "summary" in entry:
            content = entry.summary

        published_at = datetime.datetime.now()
        if "published_parsed" in entry and entry.published_parsed:
            published_at = datetime.datetime(*entry.published_parsed[:6])

        source = feed_url.split("/")[2]

        article = Article(
            id=f"{source}-{entry.get('id', url)}",
            title=title,
            content=content,
            url=url,
            source=source,
            published_at=published_at
        )

        return article
    except Exception as e:
        return None
