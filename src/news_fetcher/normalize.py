"""
Article normalization functionality for news-fetcher application.

This module provides functions to normalize and clean news articles, including text
cleaning, URL validation, date extraction, and deduplication.
"""

import re
from typing import List, Optional, Dict
from datetime import datetime
import html
from urllib.parse import urlparse, urlunparse
from bs4 import BeautifulSoup
from .models import Article
from .exceptions import ProcessingError


def normalize_article(article: Article) -> Article:
    """
    Normalize a single Article object.

    Args:
        article: Article to normalize

    Returns:
        Normalized Article object

    Raises:
        ProcessingError: If normalization fails
    """
    try:
        normalized_article = Article(
            id=article.id,
            title=normalize_title(article.title),
            content=normalize_text(article.content),
            url=normalize_url(article.url),
            source=article.source,
            published_at=article.published_at,
            fetched_at=article.fetched_at,
            author=article.author,
            summary=article.summary,
            embeddings=article.embeddings,
            cluster_id=article.cluster_id,
            score=article.score
        )
        return normalized_article
    except Exception as e:
        raise ProcessingError(f"Failed to normalize article: {e}")


def normalize_text(text: str) -> str:
    """
    Clean and normalize text content.

    Args:
        text: Text to normalize

    Returns:
        Cleaned and normalized text

    Raises:
        ProcessingError: If normalization fails
    """
    try:
        text = html.unescape(text)
        soup = BeautifulSoup(text, "html.parser")
        text = soup.get_text(separator=" ")

        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\n\s*\n", "\n", text)
        text = text.strip()

        return text
    except Exception as e:
        raise ProcessingError(f"Failed to normalize text: {e}")


def normalize_title(title: str) -> str:
    """
    Clean and normalize article title.

    Args:
        title: Title to normalize

    Returns:
        Cleaned and normalized title

    Raises:
        ProcessingError: If normalization fails
    """
    try:
        title = html.unescape(title)
        title = BeautifulSoup(title, "html.parser").get_text()
        title = re.sub(r"\s+", " ", title)
        title = title.strip()

        return title
    except Exception as e:
        raise ProcessingError(f"Failed to normalize title: {e}")


def normalize_url(url: str) -> str:
    """
    Normalize and validate a URL.

    Args:
        url: URL to normalize

    Returns:
        Normalized URL

    Raises:
        ProcessingError: If URL is invalid or normalization fails
    """
    try:
        parsed = urlparse(url)

        if not parsed.scheme:
            parsed = urlparse(f"http://{url}")

        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.lower(),
            parsed.params,
            parsed.query,
            parsed.fragment
        )).lower()

        return normalized
    except Exception as e:
        raise ProcessingError(f"Failed to normalize URL {url}: {e}")


def extract_published_date(entry: Dict) -> datetime:
    """
    Extract publication date from an RSS feed entry.

    Args:
        entry: RSS feed entry dictionary from feedparser

    Returns:
        Extracted publication date as datetime object, or current time if extraction fails
    """
    try:
        if "published_parsed" in entry and entry["published_parsed"]:
            return datetime(*entry["published_parsed"][:6])
        if "updated_parsed" in entry and entry["updated_parsed"]:
            return datetime(*entry["updated_parsed"][:6])
        if "pubDate" in entry:
            try:
                return datetime.strptime(entry["pubDate"], "%a, %d %b %Y %H:%M:%S %z")
            except Exception:
                pass
    except Exception:
        pass

    return datetime.now()


def dedupe_articles(articles: List[Article]) -> List[Article]:
    """
    Remove exact duplicates from a list of articles.

    Args:
        articles: List of Article objects to deduplicate

    Returns:
        List of unique Article objects

    Raises:
        ProcessingError: If deduplication fails
    """
    try:
        seen_urls = set()
        seen_titles = set()
        unique_articles = []

        for article in articles:
            normalized_title = normalize_title(article.title).lower()
            normalized_url = normalize_url(article.url).lower()

            if normalized_url not in seen_urls and normalized_title not in seen_titles:
                seen_urls.add(normalized_url)
                seen_titles.add(normalized_title)
                unique_articles.append(article)

        return unique_articles
    except Exception as e:
        raise ProcessingError(f"Failed to deduplicate articles: {e}")
