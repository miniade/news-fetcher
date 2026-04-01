"""
Main processing pipeline for news-fetcher application.

This module orchestrates the entire news processing pipeline, from fetching
articles to outputting the final results.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .cluster import ArticleClusterer
from .dedup import Deduplicator
from .diversify import DiversitySelector
from .exceptions import ProcessingError
from .github_enrich import enrich_github_projects
from .github_map import map_github_projects_to_news_items
from .github_rank import rank_github_projects
from .models import Article, Cluster, Config, Source
from .rank import ArticleRanker, calculate_engagement_proxy
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

            articles = self._process_github_project_articles(articles)
            articles = self._normalize(articles)
            articles = self._deduplicate(articles)
            articles, clusters = self._cluster(articles)
            articles = self._rank(articles, clusters)
            articles, clusters = self._apply_min_score(articles, clusters)
            articles, clusters = self._apply_source_strategy_controls(articles, clusters)
            selected_pool = articles
            articles = self._diversify(articles, limit)
            articles = self._summarize(articles)
            self._annotate_selection_explanations(articles, selected_pool)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            pruned_clusters = self._prune_clusters_for_articles(clusters, articles)
            result = PipelineResult(
                articles=articles,
                clusters=pruned_clusters,
                metadata={
                    "generated_at": end_time.isoformat(),
                    "duration_seconds": duration,
                    "total_articles": len(articles),
                    "total_clusters": len(pruned_clusters),
                    "sources_used": len(sources_to_use),
                },
            )

            logger.info(
                "Pipeline completed in %.2f seconds: %d articles, %d clusters",
                duration,
                len(result.articles),
                len(result.clusters),
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
            articles, clusters = self._apply_min_score(articles, clusters)
            articles, clusters = self._apply_source_strategy_controls(articles, clusters)
            selected_pool = articles
            articles = self._diversify(articles)
            articles = self._summarize(articles)
            self._annotate_selection_explanations(articles, selected_pool)
            clusters = self._prune_clusters_for_articles(clusters, articles)
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


    def _process_github_project_articles(self, articles: List[Article]) -> List[Article]:
        github_articles = [article for article in articles if article.item_type == "github_project"]
        if not github_articles:
            return articles

        normal_articles = [article for article in articles if article.item_type != "github_project"]
        github_articles = enrich_github_projects(github_articles)
        github_articles = rank_github_projects(github_articles)
        github_articles = map_github_projects_to_news_items(github_articles)
        github_articles = self._cap_github_project_articles(github_articles)
        return normal_articles + github_articles

    def _cap_github_project_articles(self, articles: List[Article]) -> List[Article]:
        if not articles:
            return []
        return articles[:1]

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
        return self.ranker.rank(articles, clusters=clusters)

    def _apply_min_score(
        self, articles: List[Article], clusters: List[Cluster]
    ) -> Tuple[List[Article], List[Cluster]]:
        min_score = float(self.config.thresholds.get("min_score", 0.0) or 0.0)
        if min_score <= 0:
            return articles, clusters

        filtered_articles = [article for article in articles if article.score >= min_score]
        if not filtered_articles:
            logger.info("No articles met min_score %.2f", min_score)
            return [], []

        return filtered_articles, self._prune_clusters_for_articles(clusters, filtered_articles)

    def _prune_clusters_for_articles(
        self, clusters: List[Cluster], articles: List[Article]
    ) -> List[Cluster]:
        if not clusters or not articles:
            return []

        kept_ids = {article.id for article in articles}
        filtered_clusters: List[Cluster] = []
        for cluster in clusters:
            cluster_articles = [article for article in cluster.articles if article.id in kept_ids]
            if not cluster_articles:
                continue

            cluster.articles = cluster_articles
            if (
                cluster.representative_article is None
                or cluster.representative_article.id not in kept_ids
            ):
                cluster.representative_article = max(cluster_articles, key=lambda article: article.score)
            filtered_clusters.append(cluster)

        return filtered_clusters

    def _apply_source_strategy_controls(
        self, articles: List[Article], clusters: List[Cluster]
    ) -> Tuple[List[Article], List[Cluster]]:
        if not articles:
            return [], []

        source_by_name = {source.name: source for source in self.config.sources}
        filtered_articles = self._filter_by_recency_window(articles, source_by_name)
        if not filtered_articles:
            logger.info("No articles remained after recency-window filtering")
            return [], []

        cluster_support = self._build_cluster_support_map(filtered_articles)
        filtered_articles = self._filter_corroboration_only_articles(
            filtered_articles,
            source_by_name,
            cluster_support,
        )
        if not filtered_articles:
            logger.info("No articles remained after corroboration-only filtering")
            return [], []

        filtered_articles = self._apply_source_score_multipliers(filtered_articles, source_by_name)
        filtered_articles.sort(key=lambda article: article.score, reverse=True)
        return filtered_articles, self._prune_clusters_for_articles(clusters, filtered_articles)

    def _filter_by_recency_window(
        self, articles: List[Article], source_by_name: Dict[str, Source]
    ) -> List[Article]:
        now = self._normalize_datetime_utc(datetime.now(timezone.utc))
        filtered: List[Article] = []
        for article in articles:
            source = source_by_name.get(article.source)
            recency_window_hours = self._get_source_recency_window_hours(source)
            if recency_window_hours is None:
                filtered.append(article)
                continue

            published_at = self._normalize_datetime_utc(article.published_at)
            age_hours = max((now - published_at).total_seconds() / 3600.0, 0.0)
            if age_hours <= recency_window_hours:
                filtered.append(article)

        return filtered

    def _normalize_datetime_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def _build_cluster_support_map(self, articles: List[Article]) -> Dict[str, int]:
        support: Dict[str, set] = {}
        for article in articles:
            cluster_key = article.cluster_id or article.id
            support.setdefault(cluster_key, set()).add(article.source)
        return {cluster_key: len(sources) for cluster_key, sources in support.items()}

    def _filter_corroboration_only_articles(
        self,
        articles: List[Article],
        source_by_name: Dict[str, Source],
        cluster_support: Dict[str, int],
    ) -> List[Article]:
        min_sources = int(self.config.thresholds.get("corroboration_min_sources", 2) or 2)
        filtered: List[Article] = []
        for article in articles:
            source = source_by_name.get(article.source)
            if source is None or source.candidate_strategy != "corroboration_only":
                filtered.append(article)
                continue

            cluster_key = article.cluster_id or article.id
            if cluster_support.get(cluster_key, 1) >= min_sources:
                filtered.append(article)

        return filtered

    def _apply_source_score_multipliers(
        self, articles: List[Article], source_by_name: Dict[str, Source]
    ) -> List[Article]:
        default_multiplier = 0.75
        for article in articles:
            source = source_by_name.get(article.source)
            if not self._is_weak_source(source):
                continue

            multiplier = default_multiplier
            if source is not None and source.weak_source_weight_multiplier is not None:
                multiplier = source.weak_source_weight_multiplier
            article.score *= multiplier

        return articles

    def _is_weak_source(self, source: Optional[Source]) -> bool:
        if source is None:
            return False
        if source.weak_source is not None:
            return source.weak_source
        return source.candidate_strategy in {"latest", "corroboration_only"} and source.source_type in {
            "plain_rss",
            "generic_html",
            "platform_feed",
            "publisher_section",
        }

    def _get_source_recency_window_hours(self, source: Optional[Source]) -> Optional[float]:
        if source is not None and source.recency_window_hours is not None:
            if source.recency_window_hours <= 0:
                return None
            return source.recency_window_hours

        if not self._is_weak_source(source):
            return None

        default_window = float(
            self.config.thresholds.get("weak_source_recency_window_hours", 0.0) or 0.0
        )
        if default_window <= 0:
            return None
        return default_window

    def _diversify(
        self, articles: List[Article], limit: Optional[int] = None
    ) -> List[Article]:
        k = limit if limit is not None else min(len(articles), 50)
        raw_max_per_source = self.config.thresholds.get("max_per_source")
        max_per_source = None
        if raw_max_per_source is not None and int(raw_max_per_source) > 0:
            max_per_source = int(raw_max_per_source)
        weak_source_max = int(self.config.thresholds.get("weak_source_max_per_source", 1) or 0)
        source_limits = self._build_source_limits(max_per_source, weak_source_max)
        return self.diversity_selector.select(
            articles,
            k=k,
            max_per_source=max_per_source,
            per_source_limits=source_limits if source_limits else None,
        )

    def _build_source_limits(
        self, max_per_source: Optional[int], weak_source_max: int
    ) -> Dict[str, int]:
        source_limits: Dict[str, int] = {}
        for source in self.config.sources:
            source_limit = source.contribution_limit
            if source_limit is None and self._is_weak_source(source) and weak_source_max > 0:
                source_limit = weak_source_max

            if source_limit is None:
                continue

            source_limits[source.name] = source_limit

        return source_limits

    def _summarize(self, articles: List[Article]) -> List[Article]:
        for article in articles:
            if not article.summary and article.content:
                article.summary = self.summarizer.summarize_text(
                    article.content,
                    title=article.title,
                )
        return articles

    def _annotate_selection_explanations(
        self,
        selected_articles: List[Article],
        candidate_pool: List[Article],
    ) -> None:
        if not selected_articles:
            return

        source_by_name = {source.name: source for source in self.config.sources}
        cluster_support = self._build_cluster_support_map(candidate_pool)

        for article in selected_articles:
            built_reasons = self._build_selection_reasons(article, cluster_support)
            built_adjustments = self._build_selection_adjustments(
                article,
                source_by_name.get(article.source),
            )
            article.selection_reasons = self._merge_reason_entries(
                article.selection_reasons,
                built_reasons,
            )
            article.selection_adjustments = self._merge_reason_entries(
                article.selection_adjustments,
                built_adjustments,
            )

    def _merge_reason_entries(
        self,
        existing: List[Dict[str, Any]],
        generated: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        merged: List[Dict[str, Any]] = []
        seen = set()
        for entry in (existing or []) + (generated or []):
            key = tuple(sorted(entry.items()))
            if key in seen:
                continue
            seen.add(key)
            merged.append(entry)
        return merged

    def _build_selection_reasons(
        self,
        article: Article,
        cluster_support: Dict[str, int],
    ) -> List[Dict[str, Any]]:
        reasons: List[Dict[str, Any]] = []

        if article.source_official_flag:
            reasons.append({"kind": "official_release"})
        if article.source_curated_flag:
            reasons.append({"kind": "curated_inclusion"})
        if article.source_rank_position is not None and article.source_rank_position > 0:
            reasons.append(
                {
                    "kind": "frontpage_rank",
                    "position": article.source_rank_position,
                }
            )

        engagement_proxy = calculate_engagement_proxy(article)
        if engagement_proxy > 0:
            reasons.append(
                {
                    "kind": "engagement_proxy",
                    "value": round(engagement_proxy, 3),
                }
            )

        cluster_key = article.cluster_id or article.id
        independent_sources = cluster_support.get(cluster_key, 1)
        min_sources = int(self.config.thresholds.get("corroboration_min_sources", 2) or 2)
        if independent_sources >= min_sources:
            reasons.append(
                {
                    "kind": "independent_source_corroboration",
                    "source_count": independent_sources,
                }
            )

        return reasons

    def _build_selection_adjustments(
        self,
        article: Article,
        source: Optional[Source],
    ) -> List[Dict[str, Any]]:
        adjustments: List[Dict[str, Any]] = []
        if not self._is_weak_source(source):
            return adjustments

        multiplier = 0.75
        if source is not None and source.weak_source_weight_multiplier is not None:
            multiplier = source.weak_source_weight_multiplier

        if multiplier < 1.0:
            adjustments.append(
                {
                    "kind": "weak_source_downgrade",
                    "multiplier": multiplier,
                }
            )

        return adjustments


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
