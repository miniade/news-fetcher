"""News Fetcher package."""

import re
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path


_DEFAULT_VERSION = "0.1.4"


def _resolve_version() -> str:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    if pyproject_path.exists():
        try:
            match = re.search(
                r'^version\s*=\s*["\']([^"\']+)["\']\s*$',
                pyproject_path.read_text(encoding="utf-8"),
                flags=re.MULTILINE,
            )
            if match:
                return match.group(1)
        except Exception:
            pass

    try:
        return package_version("news-fetcher")
    except PackageNotFoundError:
        return _DEFAULT_VERSION


__version__ = _resolve_version()

from .models import Article, Cluster, Source, Config
from .dedup import SimHash, Deduplicator, compute_shingles, jaccard_similarity
from .cluster import (
    ArticleClusterer,
    ClusterManager,
    compute_cluster_centroid,
    find_representative_article,
    calculate_cluster_similarity,
)
from .pipeline import (
    NewsPipeline,
    PipelineResult,
    create_default_pipeline,
    run_pipeline_with_config,
)
from .config import get_config, load_config, validate_config
from .exceptions import (
    NewsFetcherError,
    FetchError,
    ParseError,
    ConfigError,
    ProcessingError,
    SourceError,
)
