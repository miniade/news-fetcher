"""Output formatting helpers for news-fetcher."""

import csv
import json
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import Article, Cluster


def _article_to_dict(article: Article, include_embeddings: bool = False) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "id": article.id,
        "title": article.title,
        "content": article.content,
        "url": article.url,
        "source": article.source,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "fetched_at": article.fetched_at.isoformat() if article.fetched_at else None,
        "author": article.author,
        "summary": article.summary,
        "cluster_id": article.cluster_id,
        "score": article.score,
        "candidate_strategy": article.candidate_strategy,
        "source_type": article.source_type,
        "source_rank_position": article.source_rank_position,
        "source_section": article.source_section,
        "source_engagement_score": article.source_engagement_score,
        "source_comment_count": article.source_comment_count,
        "source_view_count": article.source_view_count,
        "source_like_count": article.source_like_count,
        "source_curated_flag": article.source_curated_flag,
        "source_official_flag": article.source_official_flag,
        "source_frontpage_timestamp": (
            article.source_frontpage_timestamp.isoformat()
            if article.source_frontpage_timestamp
            else None
        ),
        "acquisition_confidence": article.acquisition_confidence,
    }
    if include_embeddings and article.embeddings is not None:
        data["embeddings"] = article.embeddings
    return data


def format_json(
    articles: List[Article],
    clusters: Optional[List[Cluster]] = None,
    include_embeddings: bool = False,
    include_cluster_vectors: bool = False,
) -> str:
    """Format articles and clusters as JSON."""
    result: Dict[str, Any] = {
        "articles": [
            _article_to_dict(article, include_embeddings=include_embeddings)
            for article in articles
        ]
    }

    if clusters is not None:
        result["clusters"] = []
        for cluster in clusters:
            cluster_data: Dict[str, Any] = {
                "id": cluster.id,
                "articles": [article.id for article in cluster.articles],
            }
            if cluster.representative_article is not None:
                cluster_data["representative"] = {
                    "id": cluster.representative_article.id,
                    "title": cluster.representative_article.title,
                    "url": cluster.representative_article.url,
                }
            if include_cluster_vectors and cluster.centroid is not None:
                cluster_data["centroid"] = cluster.centroid
            result["clusters"].append(cluster_data)

    return json.dumps(result, ensure_ascii=False, indent=2)


def format_markdown(articles: List[Article], clusters: Optional[List[Cluster]] = None) -> str:
    """Format articles and clusters as Markdown."""
    lines = ["# News Articles", ""]

    if clusters:
        for cluster in clusters:
            heading = cluster.representative_article.title if cluster.representative_article else cluster.id
            lines.append(f"## Cluster: {heading}")
            lines.append("")
            for article in cluster.articles:
                lines.append(f"- [{article.title}]({article.url})")
                lines.append(f"  - Source: {article.source}")
                if article.published_at:
                    lines.append(f"  - Published: {article.published_at.isoformat()}")
                if article.score is not None:
                    lines.append(f"  - Score: {article.score:.2f}")
                if article.summary:
                    lines.append(f"  - Summary: {article.summary}")
            lines.append("")
        return "\n".join(lines)

    for article in articles:
        lines.append(f"## [{article.title}]({article.url})")
        lines.append("")
        lines.append(f"- Source: {article.source}")
        if article.author:
            lines.append(f"- Author: {article.author}")
        if article.published_at:
            lines.append(f"- Published: {article.published_at.isoformat()}")
        if article.score is not None:
            lines.append(f"- Score: {article.score:.2f}")
        if article.summary:
            lines.append(f"- Summary: {article.summary}")
        lines.append("")
        lines.append(article.content)
        lines.append("")

    return "\n".join(lines)


def format_csv(articles: List[Article]) -> str:
    """Format articles as CSV."""
    output = StringIO()
    fieldnames = [
        "id",
        "title",
        "url",
        "source",
        "published_at",
        "fetched_at",
        "score",
        "summary",
        "content",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()

    for article in articles:
        writer.writerow(
            {
                "id": article.id,
                "title": article.title,
                "url": article.url,
                "source": article.source,
                "published_at": article.published_at.isoformat() if article.published_at else None,
                "fetched_at": article.fetched_at.isoformat() if article.fetched_at else None,
                "score": article.score,
                "summary": article.summary,
                "content": article.content,
            }
        )

    return output.getvalue()


def format_rss(articles: List[Article]) -> str:
    """Format articles as RSS 2.0."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        '  <channel>',
        '    <title>News Fetcher Results</title>',
        '    <link>https://example.com</link>',
        '    <description>News articles fetched and clustered</description>',
        '    <language>en-us</language>',
    ]

    for article in articles:
        lines.append('    <item>')
        lines.append(f'      <title>{article.title}</title>')
        lines.append(f'      <link>{article.url}</link>')
        lines.append(f'      <description>{article.summary or article.content}</description>')
        if article.published_at:
            lines.append(
                f'      <pubDate>{article.published_at.strftime("%a, %d %b %Y %H:%M:%S GMT")}</pubDate>'
            )
        lines.append(f'      <guid>{article.id}</guid>')
        lines.append('    </item>')

    lines.extend(['  </channel>', '</rss>'])
    return "\n".join(lines)


class OutputFormatter:
    """Main output formatting interface."""

    VALID_FORMATS = ("json", "markdown", "csv", "rss")

    def __init__(
        self,
        output_format: str = "json",
        include_embeddings: bool = False,
        include_cluster_vectors: bool = False,
    ):
        if output_format not in self.VALID_FORMATS:
            raise ValueError(
                f"Invalid output format: {output_format}. Valid formats: {', '.join(self.VALID_FORMATS)}"
            )
        self.output_format = output_format
        self.include_embeddings = include_embeddings
        self.include_cluster_vectors = include_cluster_vectors

    def format(self, articles: List[Article], clusters: Optional[List[Cluster]] = None) -> str:
        if self.output_format == "json":
            return format_json(
                articles,
                clusters,
                include_embeddings=self.include_embeddings,
                include_cluster_vectors=self.include_cluster_vectors,
            )
        if self.output_format == "markdown":
            return format_markdown(articles, clusters)
        if self.output_format == "csv":
            return format_csv(articles)
        if self.output_format == "rss":
            return format_rss(articles)
        raise ValueError(f"Unknown output format: {self.output_format}")

    def save(
        self,
        articles: List[Article],
        filepath: str,
        clusters: Optional[List[Cluster]] = None,
        output_format: Optional[str] = None,
    ) -> None:
        if output_format is None:
            formatter = self
        else:
            formatter = OutputFormatter(output_format)
        content = formatter.format(articles, clusters)
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
