"""GitHub project discovery fetchers for news-fetcher."""

from __future__ import annotations

import datetime
import hashlib
import re
from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .exceptions import FetchError
from .models import Article, Source

_GITHUB_TRENDING_URL = "https://github.com/trending"


def fetch_github_trending(
    url: str = _GITHUB_TRENDING_URL,
    timeout: int = 30,
    session: Optional[requests.Session] = None,
    source_name: str = "GitHub Trending",
    source_config: Optional[Source] = None,
) -> List[Article]:
    """Fetch GitHub trending repositories and map them into project candidates."""
    try:
        if session:
            response = session.get(url, timeout=timeout)
        else:
            response = requests.get(url, timeout=timeout)

        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.select("article.Box-row")

        results: List[Article] = []
        observed_at = datetime.datetime.now(datetime.timezone.utc)
        for index, node in enumerate(articles, start=1):
            article = _parse_github_trending_article(
                node,
                base_url=url,
                source_name=source_name,
                source_config=source_config,
                rank_position=index,
                observed_at=observed_at,
            )
            if article is not None:
                results.append(article)
        return results
    except requests.exceptions.RequestException as e:
        raise FetchError(url, f"HTTP request failed: {e}") from e
    except Exception as e:
        raise FetchError(url, f"Failed to parse GitHub trending page: {e}") from e


def _parse_github_trending_article(
    node,
    base_url: str,
    source_name: str,
    source_config: Optional[Source],
    rank_position: int,
    observed_at: datetime.datetime,
) -> Optional[Article]:
    repo_link = node.select_one("h2 a[href]")
    if repo_link is None:
        return None

    href = (repo_link.get("href") or "").strip()
    if not href.startswith("/"):
        return None

    repo_full_name = " ".join(repo_link.get_text(" ", strip=True).split())
    repo_full_name = repo_full_name.replace(" / ", "/")
    if "/" not in repo_full_name:
        return None

    owner, name = [part.strip() for part in repo_full_name.split("/", 1)]
    repo_url = urljoin(base_url, href)

    description_node = node.select_one("p")
    description = (
        " ".join(description_node.get_text(" ", strip=True).split())
        if description_node is not None
        else ""
    )

    language = None
    lang_node = node.select_one("span[itemprop='programmingLanguage']")
    if lang_node is not None:
        language = " ".join(lang_node.get_text(" ", strip=True).split()) or None

    stars_total = None
    star_links = [
        a
        for a in node.select("a.Link")
        if (a.get("href") or "").rstrip("/") == href.rstrip("/") + "/stargazers"
    ]
    if star_links:
        stars_total = _parse_count(star_links[0].get_text(" ", strip=True))

    stars_today = None
    text = node.get_text("\n", strip=True)
    match = re.search(r"([\d,]+)\s+stars\s+today", text, re.IGNORECASE)
    if match:
        stars_today = _parse_count(match.group(1))

    article_id = hashlib.sha1(
        f"github-project\n{repo_full_name}\n{observed_at.date().isoformat()}".encode("utf-8")
    ).hexdigest()[:16]

    item_metadata = {
        "repo_full_name": repo_full_name,
        "repo_url": repo_url,
        "owner": owner,
        "name": name,
        "description": description,
        "primary_language": language,
        "topics": [],
        "stars_total": stars_total,
        "stars_today": stars_today,
        "growth_signals": {"stars_today": stars_today} if stars_today is not None else {},
        "discovered_at": observed_at.isoformat(),
        "source_surface": "trending",
    }

    return Article(
        id=f"github-project-{article_id}",
        title=repo_full_name,
        content=description or repo_full_name,
        url=repo_url,
        source=source_name,
        published_at=observed_at,
        candidate_strategy=(
            source_config.candidate_strategy if source_config else "project_discovery"
        ),
        source_type=(
            source_config.source_type if source_config else "github_project_discovery"
        ),
        source_rank_position=rank_position,
        acquisition_confidence=0.8,
        item_type="github_project",
        item_metadata=item_metadata,
    )


def _parse_count(text: str) -> Optional[int]:
    cleaned = text.strip().replace(",", "")
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None
