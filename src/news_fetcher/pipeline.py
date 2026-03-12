"""
Main processing pipeline for news-fetcher application.

This module orchestrates the entire news processing pipeline, from fetching
articles to outputting the final results.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .models import Article, Cluster, Config, Source
from .exceptions import ProcessingError
from .dedup import Deduplicator
from .cluster import ArticleClusterer
from .rank import ArticleRanker
from .diversify import DiversitySelector
from .summarize import ArticleSummarizer

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Container for pipeline processing results."""

    articles: List[Article] = field(default_factory=list)
    clusters: List[Cluster] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.metadata:
            self.metadata = {
                "generated_at": datetime.now().isoformat(),
                "total_articles": len(self.articles),
                "total_clusters": len(self.clusters),
            }


class NewsPipeline:
    """Main news processing pipeline."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.deduplicator = Deduplicator(
            threshold=int((1 - config.thresholds.get("similarity", 0.8)) * 64)
        )
        self.clusterer = ArticleClusterer(
            min_cluster_size=int(config.thresholds.get("cluster_size", 2))
        )
        self.ranker = ArticleRanker(config)
        self.diversity_selector = DiversitySelector(lambda_param=0.6)
        self.summarizer = ArticleSummarizer(method="position", max_sentences=3)

        logger.info("NewsPipeline initialized with %d sources", len(config.sources))

    def run(
        self,
        sources: Optional[List[Source]] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> PipelineResult:
        start_time = datetime.now()
        logger.info("Starting pipeline run")

        sources_to_use = sources or self.config.sources
        if not sources_to_use:
            logger.warning("No sources configured")
            return PipelineResult(articles=[], clusters=[])

        try:
            articles = self._fetch(sources_to_use, since)
            if not articles:
                logger.warning("No articles fetched")
                return PipelineResult(articles=[], clusters=[])

            articles = self._normalize(articles)
            articles = self._deduplicate(articles)
            articles, clusters = self._cluster(articles)
            articles = self._rank(articles, clusters)
            articles = self._diversify(articles, limit)
            articles = self._summarize(articles)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            result = PipelineResult(
                articles=articles,
                clusters=clusters,
                metadata={
                    "generated_at": end_time.isoformat(),
                    "duration_seconds": duration,
                    "total_articles": len(articles),
                    "total_clusters": len(clusters),
                    "sources_used": len(sources_to_use),
                },
            )

            logger.info(
                "Pipeline completed in %.2f seconds: %d articles, %d clusters",
                duration,
                len(articles),
                len(clusters),
            )
            return result

        except Exception as e:
            logger.exception("Pipeline failed")
            raise ProcessingError(f"Pipeline failed: {e}") from e

    def run_from_fixtures(self, fixture_paths: List[str]) -> PipelineResult:
        logger.info("Running pipeline with %d fixtures", len(fixture_paths))

        articles = []
        for i, path in enumerate(fixture_paths):
            article = Article(
                id=f"fixture-{i}",
                title=f"Article from {path}",
                content="Fixture content would be parsed here",
                url=f"file://{path}",
                source="fixture",
                published_at=datetime.now(),
            )
            articles.append(article)

        if articles:
            articles = self._normalize(articles)
            articles = self._deduplicate(articles)
            articles, clusters = self._cluster(articles)
            articles = self._rank(articles, clusters)
            articles = self._diversify(articles)
            articles = self._summarize(articles)
        else:
            clusters = []

        return PipelineResult(
            articles=articles,
            clusters=clusters,
            metadata={
                "generated_at": datetime.now().isoformat(),
                "total_articles": len(articles),
                "total_clusters": len(clusters),
                "source": "fixtures",
            },
        )

    def _fetch(self, sources: List[Source], since: Optional[datetime]) -> List[Article]:
        from .fetch import fetch_all

        return fetch_all(sources, since)

    def _normalize(self, articles: List[Article]) -> List[Article]:
        from .normalize import normalize_article

        return [normalize_article(a) for a in articles]

    def _deduplicate(self, articles: List[Article]) -> List[Article]:
        seen_hashes = {}
        unique_articles = []

        for article in articles:
            if not article.content:
                continue

            fingerprint = self.deduplicator.simhash.compute(article.content)
            is_duplicate = False
            for existing_hash in seen_hashes.values():
                if self.deduplicator.is_duplicate(fingerprint, existing_hash):
                    is_duplicate = True
                    break

            if not is_duplicate:
                seen_hashes[article.id] = fingerprint
                unique_articles.append(article)

        return unique_articles

    def _cluster(self, articles: List[Article]) -> Tuple[List[Article], List[Cluster]]:
        if not articles:
            return [], []

        clusters = self.clusterer.fit(articles)
        for cluster in clusters:
            for article in cluster.articles:
                article.cluster_id = cluster.id

        return articles, clusters

    def _rank(self, articles: List[Article], clusters: List[Cluster]) -> List[Article]:
        return self.ranker.rank(articles)

    def _diversify(
        self, articles: List[Article], limit: Optional[int] = None
    ) -> List[Article]:
        k = limit if limit is not None else min(len(articles), 50)
        raw_max_per_source = self.config.thresholds.get("max_per_source")
        max_per_source = None
        if raw_max_per_source is not None and int(raw_max_per_source) > 0:
            max_per_source = int(raw_max_per_source)
        return self.diversity_selector.select(
            articles,
            k=k,
            max_per_source=max_per_source,
        )

    def _summarize(self, articles: List[Article]) -> List[Article]:
        for article in articles:
            if not article.summary and article.content:
                article.summary = self.summarizer.summarize_text(
                    article.content,
                    title=article.title,
                )
        return articles


def create_default_pipeline(config_path: Optional[str] = None) -> NewsPipeline:
    if config_path:
        from .config import load_config

        config = load_config(config_path)
    else:
        config = Config()

    return NewsPipeline(config)


def run_pipeline_with_config(
    config: Config,
    sources: Optional[List[Source]] = None,
    since: Optional[datetime] = None,
) -> PipelineResult:
    pipeline = NewsPipeline(config)
    return pipeline.run(sources=sources, since=since)
