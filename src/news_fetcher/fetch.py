"""News fetching functionality for news-fetcher application."""

import datetime
import hashlib
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

from .exceptions import FetchError
from .models import Article, Source


def fetch_rss(
    url: str,
    timeout: int = 30,
    session: Optional[requests.Session] = None,
    source_name: Optional[str] = None,
    source_config: Optional[Source] = None,
) -> List[Article]:
    """Fetch and parse an RSS feed from the given URL."""
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
        for index, entry in enumerate(feed.entries, start=1):
            article = _parse_rss_entry(
                entry,
                url,
                source_name=source_name,
                acquisition_metadata=_build_acquisition_metadata(
                    source_config=source_config,
                    rank_position=index,
                ),
            )
            if article is not None:
                articles.append(article)
        return articles
    except requests.exceptions.RequestException as e:
        raise FetchError(url, f"HTTP request failed: {e}") from e
    except Exception as e:
        raise FetchError(url, f"Failed to parse RSS feed: {e}") from e


def fetch_html(
    url: str,
    selector: Optional[str] = None,
    timeout: int = 30,
    session: Optional[requests.Session] = None,
    source_name: Optional[str] = None,
    source_config: Optional[Source] = None,
) -> List[Article]:
    """Fetch and parse an HTML page to extract articles."""
    try:
        if session:
            response = session.get(url, timeout=timeout)
        else:
            response = requests.get(url, timeout=timeout)

        response.raise_for_status()
        response.encoding = response.apparent_encoding

        soup = BeautifulSoup(response.text, "html.parser")
        if _is_frontpage_html_source(source_config):
            return _fetch_frontpage_html(
                soup=soup,
                base_url=url,
                selector=selector,
                source_name=source_name,
                source_config=source_config,
            )

        candidates = soup.select(selector) if selector else soup.find_all("article")
        if not candidates:
            candidates = soup.select("main a[href], body a[href]")

        return _extract_html_articles(
            candidates=candidates,
            base_url=url,
            source_name=source_name,
            source_config=source_config,
        )
    except requests.exceptions.RequestException as e:
        raise FetchError(url, f"HTTP request failed: {e}") from e
    except Exception as e:
        raise FetchError(url, f"Failed to parse HTML page: {e}") from e


def fetch_all(
    sources: List[Source], since: Optional[datetime.datetime] = None
) -> List[Article]:
    """Fetch news articles from multiple sources with time filtering."""
    articles = []
    with requests.Session() as session:
        for source in sources:
            if should_fetch(source, since):
                try:
                    if source.type == "rss":
                        source_articles = fetch_rss(
                            source.url,
                            session=session,
                            source_name=source.name,
                            source_config=source,
                        )
                    else:
                        source_articles = fetch_html(
                            source.url,
                            selector=source.selector,
                            session=session,
                            source_name=source.name,
                            source_config=source,
                        )

                    if since:
                        source_articles = [
                            article for article in source_articles if article.published_at >= since
                        ]

                    articles.extend(source_articles)
                except FetchError:
                    continue

    return articles


def should_fetch(source: Source, since: Optional[datetime.datetime]) -> bool:
    """Check if a source should be fetched based on last fetch time."""
    return True


def _parse_rss_entry(
    entry: dict,
    feed_url: str,
    source_name: Optional[str] = None,
    acquisition_metadata: Optional[Dict[str, object]] = None,
) -> Optional[Article]:
    """Parse a single RSS feed entry into an Article object."""
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

        source = source_name or feed_url.split("/")[2]
        return Article(
            id=f"{source}-{entry.get('id', url)}",
            title=title,
            content=content,
            url=url,
            source=source,
            published_at=published_at,
            **(acquisition_metadata or {}),
        )
    except Exception:
        return None


def _parse_html_candidate(
    node,
    base_url: str,
    source_name: Optional[str] = None,
    acquisition_metadata: Optional[Dict[str, object]] = None,
) -> Optional[Article]:
    """Parse a generic HTML node into an article when possible."""
    link = node if getattr(node, "name", None) == "a" else node.select_one(
        "h1 a[href], h2 a[href], h3 a[href], h4 a[href], a[href]"
    )
    if link is None:
        return None

    href = (link.get("href") or "").strip()
    if not href or href.startswith(("#", "javascript:", "mailto:")):
        return None

    article_url = urljoin(base_url, href)
    parsed_url = urlparse(article_url)
    if parsed_url.scheme not in {"http", "https"}:
        return None

    title = " ".join(link.get_text(" ", strip=True).split())
    if len(title) < 8:
        return None

    if getattr(node, "name", None) == "a":
        content = title
    else:
        paragraph = node.find("p")
        content = paragraph.get_text(" ", strip=True) if paragraph else node.get_text(" ", strip=True)
    content = " ".join(content.split()) or title

    published_at = _extract_html_published_at(node)
    source = source_name or parsed_url.netloc
    article_key = hashlib.sha1(f"{article_url}\n{title}".encode("utf-8")).hexdigest()[:12]

    return Article(
        id=f"{source}-{article_key}",
        title=title,
        content=content,
        url=article_url,
        source=source,
        published_at=published_at,
        **(acquisition_metadata or {}),
    )


def _build_acquisition_metadata(
    source_config: Optional[Source],
    rank_position: Optional[int] = None,
    acquisition_confidence: Optional[float] = None,
) -> Dict[str, object]:
    """Build sparse acquisition metadata from configured source details."""
    if source_config is None:
        return {}

    source_type = source_config.source_type
    candidate_strategy = source_config.candidate_strategy

    metadata: Dict[str, object] = {
        "candidate_strategy": candidate_strategy,
        "source_type": source_type,
        "source_rank_position": rank_position,
        "source_section": source_config.selector if source_config.type == "html" else None,
        "source_curated_flag": source_type == "curated_editorial" if source_type else None,
        "source_official_flag": source_type == "official_blog" if source_type else None,
        "acquisition_confidence": acquisition_confidence,
    }
    return metadata


def _is_frontpage_html_source(source_config: Optional[Source]) -> bool:
    """Return True when the source is configured for ordered frontpage extraction."""
    return bool(
        source_config is not None
        and source_config.type == "html"
        and source_config.candidate_strategy in {"frontpage", "section_frontpage"}
    )


def _fetch_frontpage_html(
    soup: BeautifulSoup,
    base_url: str,
    selector: Optional[str],
    source_name: Optional[str],
    source_config: Optional[Source],
) -> List[Article]:
    """Fetch HTML candidates in visible frontpage order with a defined fallback."""
    candidates = _select_frontpage_candidates(soup, selector)
    articles = _extract_html_articles(
        candidates=candidates,
        base_url=base_url,
        source_name=source_name,
        source_config=source_config,
        acquisition_confidence=0.9 if selector else 0.75,
    )
    if articles:
        return articles

    fallback_candidates = soup.select("main a[href], body a[href]")
    return _extract_html_articles(
        candidates=fallback_candidates,
        base_url=base_url,
        source_name=source_name,
        source_config=source_config,
        acquisition_confidence=0.4,
    )


def _select_frontpage_candidates(soup: BeautifulSoup, selector: Optional[str]):
    """Select simple ordered list/card candidates for frontpage-style pages."""
    if selector:
        return soup.select(selector)

    candidates = soup.select("main article, main li, body article, body li")
    if candidates:
        return candidates

    return soup.find_all("article")


def _extract_html_articles(
    candidates,
    base_url: str,
    source_name: Optional[str],
    source_config: Optional[Source],
    acquisition_confidence: Optional[float] = None,
) -> List[Article]:
    """Parse HTML candidates while preserving first-seen page order metadata."""
    articles: List[Article] = []
    seen_urls = set()
    for index, candidate in enumerate(candidates, start=1):
        article = _parse_html_candidate(
            candidate,
            base_url=base_url,
            source_name=source_name,
            acquisition_metadata=_build_acquisition_metadata(
                source_config=source_config,
                rank_position=index,
                acquisition_confidence=acquisition_confidence,
            ),
        )
        if article is None or article.url in seen_urls:
            continue
        seen_urls.add(article.url)
        articles.append(article)

    return articles


def _extract_html_published_at(node) -> datetime.datetime:
    """Best-effort extraction of publication time from an HTML node."""
    time_element = getattr(node, "find", lambda *_args, **_kwargs: None)("time")
    if time_element is not None:
        raw_value = (time_element.get("datetime") or time_element.get_text(" ", strip=True) or "").strip()
        parsed = _parse_datetime(raw_value)
        if parsed is not None:
            return parsed
    return datetime.datetime.now()


def _parse_datetime(value: str) -> Optional[datetime.datetime]:
    """Parse a small set of common datetime string formats."""
    if not value:
        return None

    candidate = value.strip()
    iso_candidate = candidate.replace("Z", "+00:00")
    try:
        parsed = datetime.datetime.fromisoformat(iso_candidate)
        if parsed.tzinfo is not None:
            return parsed.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return parsed
    except ValueError:
        pass

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%a, %d %b %Y %H:%M:%S %z",
    ):
        try:
            parsed = datetime.datetime.strptime(candidate, fmt)
            if parsed.tzinfo is not None:
                return parsed.astimezone(datetime.timezone.utc).replace(tzinfo=None)
            return parsed
        except ValueError:
            continue

    return None
