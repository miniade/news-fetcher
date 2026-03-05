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

# Import processing modules
from .dedup import Deduplicator
from .cluster import ArticleClusterer
from .rank import ArticleRanker
from .diversify import DiversitySelector
from .summarize import ArticleSummarizer

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """
    Container for pipeline processing results.

    Attributes:
        articles: List of processed articles
        clusters: List of article clusters
        metadata: Processing metadata (timestamps, counts, etc.)
    """
    articles: List[Article] = field(default_factory=list)
    clusters: List[Cluster] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize metadata with defaults if empty."""
        if not self.metadata:
            self.metadata = {
                "generated_at": datetime.now().isoformat(),
                "total_articles": len(self.articles),
                "total_clusters": len(self.clusters),
            }


class NewsPipeline:
    """
    Main news processing pipeline.

    This class orchestrates the entire news processing workflow, from fetching
    articles to outputting the final results.

    Attributes:
        config: Pipeline configuration
        deduplicator: Deduplication component
        clusterer: Clustering component
        ranker: Ranking component
        diversity_selector: Diversity selection component
        summarizer: Summarization component
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize the pipeline with configuration.

        Args:
            config: Pipeline configuration
        """
        self.config = config

        # Initialize components
        self.deduplicator = Deduplicator(
            threshold=int((1 - config.thresholds.get("similarity", 0.8)) * 64)
        )
        self.clusterer = ArticleClusterer(
            min_cluster_size=int(config.thresholds.get("cluster_size", 2))
        )
        self.ranker = ArticleRanker(config)
        self.diversity_selector = DiversitySelector(
            lambda_param=0.6
        )
        self.summarizer = ArticleSummarizer(
            method="position",
            max_sentences=3
        )

        logger.info("NewsPipeline initialized with %d sources", len(config.sources))

    def run(
        self,
        sources: Optional[List[Source]] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> PipelineResult:
        """
        Run the full pipeline with live sources.

        Args:
            sources: List of sources to fetch from (defaults to config.sources)
            since: Only fetch articles published after this time
            limit: Maximum number of articles to return

        Returns:
            PipelineResult containing processed articles and metadata
        """
        start_time = datetime.now()
        logger.info("Starting pipeline run")

        # Use provided sources or fall back to config
        sources_to_use = sources or self.config.sources

        if not sources_to_use:
            logger.warning("No sources configured")
            return PipelineResult(articles=[], clusters=[])

        try:
            # Step 1: Fetch articles
            articles = self._fetch(sources_to_use, since)
            if not articles:
                logger.warning("No articles fetched")
                return PipelineResult(articles=[], clusters=[])

            # Step 2: Normalize articles
            articles = self._normalize(articles)

            # Step 3: Deduplicate articles
            articles = self._deduplicate(articles)

            # Step 4: Cluster articles
            articles, clusters = self._cluster(articles)

            # Step 5: Rank articles
            articles = self._rank(articles, clusters)

            # Step 6: Apply diversity selection
            articles = self._diversify(articles, limit)

            # Step 7: Generate summaries
            articles = self._summarize(articles)

            # Build result
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
                }
            )

            logger.info(
                "Pipeline completed in %.2f seconds: %d articles, %d clusters",
                duration, len(articles), len(clusters)
            )

            return result

        except Exception as e:
            logger.exception("Pipeline failed")
            raise ProcessingError(f"Pipeline failed: {e}") from e

    def run_from_fixtures(self, fixture_paths: List[str]) -> PipelineResult:
        """
        Run pipeline with local fixture files instead of fetching.

        Args:
            fixture_paths: List of paths to fixture files (RSS/XML/HTML)

        Returns:
            PipelineResult containing processed articles and metadata
        """
        logger.info("Running pipeline with %d fixtures", len(fixture_paths))

        # For now, create some sample articles from fixtures
        # In a real implementation, this would parse the fixture files
        from datetime import datetime
        from .models import Article

        articles = []
        for i, path in enumerate(fixture_paths):
            # In a real implementation, parse the fixture file
            # For now, create a placeholder article
            article = Article(
                id=f"fixture-{i}",
                title=f"Article from {path}",
                content="Fixture content would be parsed here",
                url=f"file://{path}",
                source="fixture",
                published_at=datetime.now()
            )
            articles.append(article)

        # Process the articles through the pipeline
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
            }
        )

    def _fetch(self, sources: List[Source], since: Optional[datetime]) -> List[Article]:
        """Fetch articles from sources."""
        from .fetch import fetch_all
        return fetch_all(sources, since)

    def _normalize(self, articles: List[Article]) -> List[Article]:
        """Normalize articles."""
        from .normalize import normalize_article
        return [normalize_article(a) for a in articles]

    def _deduplicate(self, articles: List[Article]) -> List[Article]:
        """Remove duplicate articles."""
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
        """Cluster articles."""
        if not articles:
            return [], []

        clusters = self.clusterer.fit(articles)

        # Assign cluster IDs to articles
        for cluster in clusters:
            for article in cluster.articles:
                article.cluster_id = cluster.id

        return articles, clusters

    def _rank(self, articles: List[Article], clusters: List[Cluster]) -> List[Article]:
        """Rank articles."""
        return self.ranker.rank(articles)

    def _diversify(self, articles: List[Article], limit: Optional[int] = None) -> List[Article]:
        """Apply diversity selection."""
        k = limit if limit is not None else min(len(articles), 50)  # Use limit if provided
        return self.diversity_selector.select(articles, k=k)

    def _summarize(self, articles: List[Article]) -> List[Article]:
        """Generate summaries for articles."""
        for article in articles:
            if not article.summary and article.content:
                article.summary = self.summarizer.summarize_text(
                    article.content,
                    title=article.title
                )
        return articles


def create_default_pipeline(config_path: Optional[str] = None) -> NewsPipeline:
    """
    Create a default pipeline instance.

    Args:
        config_path: Optional path to configuration file

    Returns:
        Configured NewsPipeline instance
    """
    if config_path:
        from .config import load_config
        config = load_config(config_path)
    else:
        config = Config()

    return NewsPipeline(config)


def run_pipeline_with_config(
    config: Config,
    sources: Optional[List[Source]] = None,
    since: Optional[datetime] = None
) -> PipelineResult:
    """
    Run pipeline with given configuration.

    Args:
        config: Pipeline configuration
        sources: Optional list of sources to use
        since: Optional time filter

    Returns:
        PipelineResult with processed articles
    """
    pipeline = NewsPipeline(config)
    return pipeline.run(sources=sources, since=since)
