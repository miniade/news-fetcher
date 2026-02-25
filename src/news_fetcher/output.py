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


def format_json(articles: List[Article], clusters: Optional[List[Cluster]] = None) -> str:
    """
    Format articles and clusters as JSON.

    Args:
        articles: List of articles
        clusters: Optional list of clusters

    Returns:
        JSON string representation
    """
    data = []
    for article in articles:
        article_data = {
            "id": article.id,
            "title": article.title,
            "content": article.content,
            "url": article.url,
            "source": article.source,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "fetched_at": article.fetched_at.isoformat() if article.fetched_at else None
        }
        if article.author:
            article_data["author"] = article.author
        if article.summary:
            article_data["summary"] = article.summary
        if article.embeddings:
            article_data["embeddings"] = article.embeddings
        if article.cluster_id:
            article_data["cluster_id"] = article.cluster_id
        if article.score:
            article_data["score"] = article.score

        data.append(article_data)

    result = {"articles": data}
    if clusters:
        result["clusters"] = []
        for cluster in clusters:
            cluster_data = {
                "id": cluster.id,
                "articles": [article.id for article in cluster.articles],
                "representative": {
                    "id": cluster.representative_article.id,
                    "title": cluster.representative_article.title,
                    "url": cluster.representative_article.url
                }
            }
            if cluster.centroid:
                cluster_data["centroid"] = cluster.centroid
            result["clusters"].append(cluster_data)

    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


def format_markdown(articles: List[Article], clusters: Optional[List[Cluster]] = None) -> str:
    """
    Format articles and clusters as Markdown.

    Args:
        articles: List of articles
        clusters: Optional list of clusters

    Returns:
        Markdown string representation
    """
    output = []
    output.append("# News Articles")
    output.append("")

    if clusters:
        for cluster in clusters:
            output.append(f"## Cluster: {cluster.representative_article.title}")
            output.append("")
            for article in cluster.articles:
                output.append(f"- [{article.title}]({article.url})")
                if article.summary:
                    output.append(f"  {article.summary}")
            output.append("")
    else:
        for article in articles:
            output.append(f"## {article.title}")
            output.append("")
            if article.author:
                output.append(f"**Author:** {article.author}")
                output.append("")
            if article.published_at:
                output.append(f"**Published:** {article.published_at}")
                output.append("")
            output.append(article.content)
            output.append("")

    return "\n".join(output)


def format_csv(articles: List[Article]) -> str:
    """
    Format articles as CSV.

    Args:
        articles: List of articles

    Returns:
        CSV string representation
    """
    output = StringIO()
    fieldnames = ["id", "title", "content", "url", "source", "published_at", "fetched_at"]

    writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()

    for article in articles:
        row = {
            "id": article.id,
            "title": article.title,
            "content": article.content,
            "url": article.url,
            "source": article.source,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "fetched_at": article.fetched_at.isoformat() if article.fetched_at else None
        }
        writer.writerow(row)

    return output.getvalue()


def format_rss(articles: List[Article]) -> str:
    """
    Format articles as RSS 2.0.

    Args:
        articles: List of articles

    Returns:
        RSS 2.0 string representation
    """
    output = []
    output.append('<?xml version="1.0" encoding="UTF-8"?>')
    output.append('<rss version="2.0">')
    output.append('  <channel>')
    output.append('    <title>News Fetcher Results</title>')
    output.append('    <link>https://example.com</link>')
    output.append('    <description>News articles fetched and clustered</description>')
    output.append('    <language>en-us</language>')

    for article in articles:
        output.append('    <item>')
        output.append(f'      <title>{article.title}</title>')
        output.append(f'      <link>{article.url}</link>')
        output.append(f'      <description>{article.content}</description>')
        if article.published_at:
            output.append(f'      <pubDate>{article.published_at.strftime("%a, %d %b %Y %H:%M:%S %Z")}</pubDate>')
        output.append(f'      <guid>{article.id}</guid>')
        output.append('    </item>')

    output.append('  </channel>')
    output.append('</rss>')
    return "\n".join(output)


class OutputFormatter:
    """
    Main output formatting interface.

    Provides multiple output formats with a consistent API.
    """

    def __init__(self, output_format: str = "json"):
        """
        Initialize the OutputFormatter.

        Args:
            output_format: Output format to use. Options:
                - "json": JSON format (default)
                - "markdown": Markdown format
                - "csv": CSV format
                - "rss": RSS 2.0 format
        """
        valid_formats = ["json", "markdown", "csv", "rss"]
        if output_format not in valid_formats:
            raise ValueError(f"Invalid output format: {output_format}. "
                             f"Valid formats: {', '.join(valid_formats)}")
        self.output_format = output_format

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
        if self.output_format == "json":
            return format_json(articles, clusters)
        elif self.output_format == "markdown":
            return format_markdown(articles, clusters)
        elif self.output_format == "csv":
            return format_csv(articles)
        elif self.output_format == "rss":
            return format_rss(articles)
        else:
            raise ValueError(f"Unknown output format: {self.output_format}")

    def save(self, articles: List[Article], filepath: str,
             output_format: Optional[str] = None) -> None:
        """
        Save formatted articles to a file.

        Args:
            articles: List of articles to save
            filepath: Path to save the file
            output_format: Optional format override
        """
        fmt = output_format or self.output_format
        content = self.format(articles) if output_format is None else OutputFormatter(
            output_format).format(articles)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
