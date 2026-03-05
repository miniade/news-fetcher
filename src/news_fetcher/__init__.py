"""News Fetcher package."""

__version__ = "0.1.1"

from .models import Article, Cluster, Source, Config
from .dedup import SimHash, Deduplicator, compute_shingles, jaccard_similarity
from .cluster import ArticleClusterer, ClusterManager, compute_cluster_centroid, find_representative_article, calculate_cluster_similarity
from .pipeline import NewsPipeline, PipelineResult, create_default_pipeline, run_pipeline_with_config
from .config import get_config, load_config, validate_config
from .exceptions import NewsFetcherError, FetchError, ParseError, ConfigError, ProcessingError, SourceError
