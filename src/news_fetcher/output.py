"""
Output formatting module for news-fetcher application.

This module provides various output formats for news articles and clusters,
including JSON, Markdown, CSV, and RSS.
"""

import csv
import json
from io import StringIO
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from news_fetcher.models import Article, Cluster


class OutputFormatter:
    """
    Main output formatting interface.

    Provides multiple output formats with a consistent API.
    """

    def __init__(self, format: str = "json"):
        """
        Initialize the OutputFormatter.

        Args:
            format: Output format to use. Options:
                - "json": JSON format (default)
                - "markdown": Markdown format
                - "csv": CSV format
                - "rss": RSS 2.0 format
        """
        valid_formats = ["json", "markdown", "csv", "rss"]
        if format not in valid_formats:
            raise ValueError(f"Invalid output format: {format}. "
                             f"Valid formats: {', '.join(valid_formats)}")
        self.format = format

    def format(self, articles: List[Article],
               clusters: Optional[List[Cluster]] = None) -> str:
        """
        Format articles and clusters into the specified format.

        Args:
            articles: List of articles to format
            clusters: Optional list of clusters

        Returns:
            Formatted output as string
        """
        if self.format == "json":
            return format_json(articles, clusters)
        elif self.format == "markdown":
            return format_markdown(articles, clusters)
        elif self.format == "csv":
            return format_csv(articles)
        elif self.format == "rss":
            return format_rss(articles)
        else:
            raise ValueError(f"Unknown output format: {self.format}")

    def save(self, articles: List[Article], filepath: str,
             format: Optional[str] = None) -> None:
        """
        Save formatted articles to a file.

        Args:
            articles: List of articles to save
            filepath: Path to save the file
            format: Optional format override
        """
        output_format = format or self.format
        content = self.format(articles) if format is None else OutputFormatter(
            format).format(articles)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)


def format_timestamp(dt: datetime) -> str:
    """
    Format datetime for output.

    Args:
        dt: Datetime object to format

    Returns:
        Formatted timestamp string (ISO 8601)
    """
    return dt.isoformat()


def format_relative_time(dt: datetime) -> str:
    """
    Format datetime as relative time (e.g., "2 hours ago").

    Args:
        dt: Datetime object to format

    Returns:
        Relative time string
    """
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    delta = now - dt

    if delta.total_seconds() < 60:
        return "just now"
    elif delta.total_seconds() < 3600:
        minutes = int(delta.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif delta.total_seconds() < 86400:
        hours = int(delta.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif delta.total_seconds() < 2592000:
        days = int(delta.total_seconds() / 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"
    else:
        return dt.strftime("%B %d, %Y")


def truncate_text(text: str, max_length: int) -> str:
    """
    Truncate text with ellipsis if it exceeds maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length before truncation

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def escape_markdown(text: str) -> str:
    """
    Escape markdown special characters.

    Args:
        text: Text to escape

    Returns:
        Escaped text
    """
    escape_chars = {
        '\\': '\\\\',
        '`': '\\`',
        '*': '\\*',
        '_': '\\_',
        '{': '\\{',
        '}': '\\}',
        '[': '\\[',
        ']': '\\]',
        '(': '\\(',
        ')': '\\)',
        '#': '\\#',
        '+': '\\+',
        '-': '\\-',
        '.': '\\.',
        '!': '\\!'
    }
    return ''.join([escape_chars.get(c, c) for c in text])


def group_by_cluster(articles: List[Article]) -> Dict[str, List[Article]]:
    """
    Group articles by their cluster ID.

    Args:
        articles: List of articles to group

    Returns:
        Dictionary mapping cluster ID to list of articles
    """
    clusters = defaultdict(list)
    for article in articles:
        if article.cluster_id:
            clusters[article.cluster_id].append(article)
    return clusters


def format_json(articles: List[Article],
                clusters: Optional[List[Cluster]] = None,
                pretty: bool = True) -> str:
    """
    Format articles and clusters as JSON.

    Args:
        articles: List of articles to format
        clusters: Optional list of clusters
        pretty: Whether to use pretty formatting

    Returns:
        JSON formatted string
    """
    # Convert datetimes to strings
    def serialize_datetime(obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)

    data: Dict[str, Any] = {
        "metadata": {
            "generated_at": format_timestamp(datetime.now()),
            "total_articles": len(articles),
            "total_clusters": len(clusters) if clusters else 0
        }
    }

    if clusters:
        data["clusters"] = []
        for cluster in clusters:
            cluster_data = {
                "id": cluster.id,
                "size": len(cluster.articles),
                "score": max(article.score for article in cluster.articles) if cluster.articles else 0.0,
                "sources": list(set(article.source for article in cluster.articles)),
                "representative": vars(cluster.representative_article) if cluster.representative_article else None,
                "articles": [vars(article) for article in cluster.articles]
            }
            data["clusters"].append(cluster_data)

    data["articles"] = [vars(article) for article in articles]

    if pretty:
        return json.dumps(data, indent=2, default=serialize_datetime, ensure_ascii=False)
    else:
        return json.dumps(data, default=serialize_datetime, ensure_ascii=False)


def format_markdown(articles: List[Article],
                    clusters: Optional[List[Cluster]] = None) -> str:
    """
    Format articles and clusters as Markdown.

    Args:
        articles: List of articles to format
        clusters: Optional list of clusters

    Returns:
        Markdown formatted string
    """
    output = []
    output.append("# News Digest")
    output.append(f"Generated: {datetime.now().strftime('%B %d, %Y')}")
    output.append("")

    # Top Stories
    output.append("## Top Stories")
    output.append("")

    for article in sorted(articles, key=lambda x: x.score, reverse=True):
        output.append(f"### [{escape_markdown(article.title)}]({article.url})")
        output.append(f"**Source**: {escape_markdown(article.source)} | "
                     f"**Published**: {format_relative_time(article.published_at)}")
        if article.summary:
            output.append(f"**Summary**: {escape_markdown(article.summary)}")
        else:
            output.append(f"**Summary**: {truncate_text(escape_markdown(article.content), 200)}")
        output.append("")

    # Trending Topics (Clusters)
    if clusters:
        output.append("## Trending Topics")
        output.append("")

        for cluster in sorted(clusters, key=lambda x: len(x.articles), reverse=True):
            source_count = len(set(article.source for article in cluster.articles))
            output.append(f"- {escape_markdown(cluster.representative_article.title if cluster.representative_article else 'Untitled Topic')} "
                         f"({len(cluster.articles)} articles from {source_count} sources)")

        output.append("")

    return "\n".join(output)


def format_csv(articles: List[Article]) -> str:
    """
    Format articles as CSV for data analysis.

    Args:
        articles: List of articles to format

    Returns:
        CSV formatted string
    """
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id", "title", "content", "url", "source", "published_at",
            "fetched_at", "author", "summary", "score"
        ]
    )

    writer.writeheader()

    for article in articles:
        row = {
            "id": article.id,
            "title": article.title,
            "content": article.content,
            "url": article.url,
            "source": article.source,
            "published_at": format_timestamp(article.published_at),
            "fetched_at": format_timestamp(article.fetched_at),
            "author": article.author or "",
            "summary": article.summary or "",
            "score": article.score
        }
        writer.writerow(row)

    return output.getvalue()


def format_rss(articles: List[Article], title: str = "News Feed") -> str:
    """
    Format articles as RSS 2.0 feed.

    Args:
        articles: List of articles to format
        title: Feed title

    Returns:
        RSS 2.0 formatted string
    """
    output = []
    output.append('<?xml version="1.0" encoding="UTF-8" ?>')
    output.append(f'<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">')
    output.append(f'  <channel>')
    output.append(f'    <title>{escape_xml(title)}</title>')
    output.append(f'    <link>https://example.com/news</link>')
    output.append(f'    <description>Latest news articles</description>')
    output.append(f'    <language>en-us</language>')
    output.append(f'    <pubDate>{datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}</pubDate>')
    output.append(f'    <lastBuildDate>{datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}</lastBuildDate>')
    output.append(f'    <atom:link href="https://example.com/feed.rss" rel="self" type="application/rss+xml" />')

    for article in sorted(articles, key=lambda x: x.published_at, reverse=True):
        output.append(f'    <item>')
        output.append(f'      <title>{escape_xml(article.title)}</title>')
        output.append(f'      <link>{escape_xml(article.url)}</link>')
        output.append(f'      <description>{escape_xml(article.summary or article.content)}</description>')
        output.append(f'      <pubDate>{article.published_at.strftime("%a, %d %b %Y %H:%M:%S GMT")}</pubDate>')
        output.append(f'      <guid isPermaLink="true">{escape_xml(article.url)}</guid>')
        if article.author:
            output.append(f'      <author>{escape_xml(article.author)}</author>')
        if article.source:
            output.append(f'      <category>{escape_xml(article.source)}</category>')
        output.append(f'    </item>')

    output.append(f'  </channel>')
    output.append(f'</rss>')

    return "\n".join(output)


def escape_xml(text: str) -> str:
    """
    Escape XML special characters.

    Args:
        text: Text to escape

    Returns:
        Escaped text
    """
    escape_chars = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&apos;'
    }
    return ''.join([escape_chars.get(c, c) for c in text])
