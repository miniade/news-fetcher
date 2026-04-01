"""
Configuration management for news-fetcher application.

This module handles loading, validation, and management of configuration
from YAML/JSON files with support for environment variable overrides.
"""

import os
from os import PathLike
from typing import Any, Dict, Mapping, Optional, Set, Tuple, Union

import yaml

from .models import Config, Source


class ConfigError(Exception):
    """Exception raised for configuration-related errors."""


ConfigInput = Union[Mapping[str, Any], str, PathLike[str]]


# v1 is intentionally config-first and narrow:
# - candidate_strategy is a single enum per source, not a fallback chain
# - only a small taxonomy is modeled here so invalid combinations fail early
# - parsing/validation is the goal in this issue; fetch behavior stays unchanged
SUPPORTED_SOURCE_TYPES = {
    "plain_rss",
    "official_blog",
    "community_ranked",
    "platform_feed",
    "publisher_section",
    "curated_editorial",
    "generic_html",
    "github_project_discovery",
}

SUPPORTED_CANDIDATE_STRATEGIES = {
    "latest",
    "frontpage",
    "trending",
    "curated",
    "release",
    "community_ranked",
    "high_engagement_proxy",
    "section_frontpage",
    "corroboration_only",
    "project_discovery",
}

SUPPORTED_SOURCE_TYPES_BY_FETCH_TYPE = {
    "rss": {"plain_rss", "official_blog"},
    "html": {
        "community_ranked",
        "platform_feed",
        "publisher_section",
        "curated_editorial",
        "generic_html",
        "github_project_discovery",
    },
}

SUPPORTED_CANDIDATE_STRATEGIES_BY_SOURCE_TYPE = {
    "plain_rss": {"latest", "corroboration_only"},
    "official_blog": {"latest", "release", "corroboration_only"},
    "community_ranked": {"frontpage", "community_ranked", "corroboration_only"},
    "platform_feed": {
        "trending",
        "high_engagement_proxy",
        "frontpage",
        "latest",
        "corroboration_only",
    },
    "publisher_section": {"section_frontpage", "frontpage", "latest", "corroboration_only"},
    # Curated/editorial sources are modeled as strong positive signals, not weak
    # corroboration inputs, so corroboration_only is intentionally excluded.
    "curated_editorial": {"curated", "frontpage", "section_frontpage"},
    "generic_html": {"frontpage", "section_frontpage", "latest", "corroboration_only"},
    "github_project_discovery": {"project_discovery"},
}


def _format_choices(values: Set[str]) -> str:
    return ", ".join(sorted(values))


def _parse_source_strategy_fields(
    source_data: Mapping[str, Any]
) -> Tuple[Optional[str], Optional[str]]:
    source_type_raw = source_data.get("source_type")
    strategy_raw = source_data.get("candidate_strategy")

    source_type = str(source_type_raw) if source_type_raw is not None else None
    strategy = str(strategy_raw) if strategy_raw is not None else None

    if bool(source_type) != bool(strategy):
        raise ConfigError(
            "source_type and candidate_strategy must be set together when either is provided"
        )

    if source_type is None and strategy is None:
        return None, None

    if source_type not in SUPPORTED_SOURCE_TYPES:
        raise ConfigError(
            f"Unsupported source_type '{source_type}'. Supported values: "
            f"{_format_choices(SUPPORTED_SOURCE_TYPES)}"
        )

    if strategy not in SUPPORTED_CANDIDATE_STRATEGIES:
        raise ConfigError(
            f"Unsupported candidate_strategy '{strategy}'. Supported values: "
            f"{_format_choices(SUPPORTED_CANDIDATE_STRATEGIES)}"
        )

    return source_type, strategy


def _validate_source_strategy_combo(
    *,
    source_name: str,
    fetch_type: str,
    source_type: Optional[str],
    strategy: Optional[str],
) -> None:
    if source_type is None or strategy is None:
        return

    allowed_source_types = SUPPORTED_SOURCE_TYPES_BY_FETCH_TYPE.get(fetch_type)
    if allowed_source_types is None:
        raise ConfigError(
            f"Source '{source_name}' has unsupported type '{fetch_type}'. Supported values: "
            f"{_format_choices(set(SUPPORTED_SOURCE_TYPES_BY_FETCH_TYPE))}"
        )
    if source_type not in allowed_source_types:
        raise ConfigError(
            f"Source '{source_name}' uses type '{fetch_type}', which does not support "
            f"source_type '{source_type}'. Allowed source_type values for {fetch_type}: "
            f"{_format_choices(allowed_source_types)}"
        )

    allowed_strategies = SUPPORTED_CANDIDATE_STRATEGIES_BY_SOURCE_TYPE[source_type]
    if strategy not in allowed_strategies:
        raise ConfigError(
            f"Source '{source_name}' does not support candidate_strategy '{strategy}' "
            f"for source_type '{source_type}'. Allowed strategies: "
            f"{_format_choices(allowed_strategies)}"
        )


def _parse_acquisition_controls(source_data: Mapping[str, Any]) -> Dict[str, Any]:
    raw_acquisition = source_data.get("acquisition") or {}
    if not isinstance(raw_acquisition, Mapping):
        raise ConfigError("Source 'acquisition' must be an object")

    controls: Dict[str, Any] = {}

    weak_source = raw_acquisition.get("weak_source")
    if weak_source is not None:
        if not isinstance(weak_source, bool):
            raise ConfigError("Source acquisition.weak_source must be a boolean")
        controls["weak_source"] = weak_source

    weak_source_weight_multiplier = raw_acquisition.get("weak_source_weight_multiplier")
    if weak_source_weight_multiplier is not None:
        controls["weak_source_weight_multiplier"] = float(weak_source_weight_multiplier)
        if controls["weak_source_weight_multiplier"] < 0:
            raise ConfigError(
                "Source acquisition.weak_source_weight_multiplier must be >= 0"
            )

    contribution_limit = raw_acquisition.get("contribution_limit")
    if contribution_limit is not None:
        controls["contribution_limit"] = int(contribution_limit)
        if controls["contribution_limit"] < 0:
            raise ConfigError("Source acquisition.contribution_limit must be >= 0")

    recency_window_hours = raw_acquisition.get("recency_window_hours")
    if recency_window_hours is not None:
        controls["recency_window_hours"] = float(recency_window_hours)
        if controls["recency_window_hours"] < 0:
            raise ConfigError("Source acquisition.recency_window_hours must be >= 0")

    return controls


def _load_config_data(config_input: ConfigInput) -> Dict[str, Any]:
    """Load raw configuration data from a mapping or a file path."""
    if isinstance(config_input, (str, PathLike)):
        config_path = os.fspath(config_input)
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
        except Exception as e:
            raise ConfigError(f"Failed to parse configuration file: {e}") from e
    else:
        config_data = config_input

    if config_data is None:
        return {}
    if not isinstance(config_data, Mapping):
        raise ConfigError("Configuration root must be an object/mapping")

    return dict(config_data)


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from a YAML/JSON file.

    Args:
        config_path: Path to the configuration file. If None, looks for
            config.yaml in the current directory.

    Returns:
        Loaded and validated configuration object.

    Raises:
        FileNotFoundError: If configuration file is not found.
        ConfigError: If configuration is invalid.
    """
    if config_path is None:
        config_path = "config.yaml"

    return validate_config(config_path)


def validate_config(config_input: ConfigInput) -> Config:
    """
    Validate and parse configuration data.

    Args:
        config_input: Raw configuration mapping or a path to a config file.

    Returns:
        Validated Config object.

    Raises:
        ConfigError: If configuration is invalid.
    """
    try:
        config_data = _load_config_data(config_input)

        raw_sources = config_data.get("sources", [])
        if not isinstance(raw_sources, list):
            raise ConfigError("'sources' must be a list")

        sources = []
        for source_data in raw_sources:
            if not isinstance(source_data, Mapping):
                raise ConfigError("Each source must be an object")
            if "name" not in source_data or "url" not in source_data:
                raise ConfigError("Source must have name and url fields")

            source_name = str(source_data["name"])
            fetch_type = str(source_data.get("type", "rss"))
            selector = source_data.get("selector")
            source_type, candidate_strategy = _parse_source_strategy_fields(source_data)
            acquisition_controls = _parse_acquisition_controls(source_data)
            _validate_source_strategy_combo(
                source_name=source_name,
                fetch_type=fetch_type,
                source_type=source_type,
                strategy=candidate_strategy,
            )

            sources.append(
                Source(
                    name=source_name,
                    url=str(source_data["url"]),
                    weight=float(source_data.get("weight", 1.0)),
                    type=fetch_type,
                    selector=str(selector) if selector is not None else None,
                    source_type=source_type,
                    candidate_strategy=candidate_strategy,
                    weak_source=acquisition_controls.get("weak_source"),
                    weak_source_weight_multiplier=acquisition_controls.get(
                        "weak_source_weight_multiplier"
                    ),
                    contribution_limit=acquisition_controls.get("contribution_limit"),
                    recency_window_hours=acquisition_controls.get("recency_window_hours"),
                )
            )

        raw_thresholds = config_data.get("thresholds") or {}
        if not isinstance(raw_thresholds, Mapping):
            raise ConfigError("'thresholds' must be an object")
        thresholds = dict(raw_thresholds)
        default_thresholds = {
            "similarity": 0.8,
            "min_score": 0.3,
            "cluster_size": 2,
            "max_per_source": 3,
            "weak_source_max_per_source": 1,
            "weak_source_recency_window_hours": 0.0,
            "corroboration_min_sources": 2,
        }
        for key, default in default_thresholds.items():
            value = thresholds.get(key, default)
            if key in {
                "cluster_size",
                "max_per_source",
                "weak_source_max_per_source",
                "corroboration_min_sources",
            }:
                thresholds[key] = int(value)
            else:
                thresholds[key] = float(value)

        if thresholds["cluster_size"] < 1:
            raise ConfigError("thresholds.cluster_size must be >= 1")
        if thresholds["max_per_source"] < 0:
            raise ConfigError("thresholds.max_per_source must be >= 0")
        if thresholds["weak_source_max_per_source"] < 0:
            raise ConfigError("thresholds.weak_source_max_per_source must be >= 0")
        if thresholds["weak_source_recency_window_hours"] < 0:
            raise ConfigError("thresholds.weak_source_recency_window_hours must be >= 0")
        if thresholds["corroboration_min_sources"] < 1:
            raise ConfigError("thresholds.corroboration_min_sources must be >= 1")
        if thresholds["min_score"] < 0:
            raise ConfigError("thresholds.min_score must be >= 0")

        raw_weights = config_data.get("weights") or {}
        if not isinstance(raw_weights, Mapping):
            raise ConfigError("'weights' must be an object")
        weights = dict(raw_weights)
        default_weights = {
            "content": 0.6,
            "source": 0.2,
            "publish_time": 0.2,
        }
        for key, default in default_weights.items():
            weights[key] = float(weights.get(key, default))

        return Config(sources=sources, thresholds=thresholds, weights=weights)

    except ConfigError:
        raise
    except Exception as e:
        raise ConfigError(f"Invalid configuration: {e}") from e


def load_config_from_env(config: Config) -> Config:
    """
    Override configuration values from environment variables.

    Args:
        config: Base configuration object.

    Returns:
        Configuration object with environment variable overrides applied.
    """
    prefix = "NEWS_FETCHER_"

    for key in config.thresholds:
        env_key = f"{prefix}THRESHOLD_{key.upper()}"
        if env_key in os.environ:
            try:
                if key in {"cluster_size", "max_per_source"}:
                    config.thresholds[key] = int(os.environ[env_key])
                else:
                    config.thresholds[key] = float(os.environ[env_key])
            except ValueError:
                pass

    for key in config.weights:
        env_key = f"{prefix}WEIGHT_{key.upper()}"
        if env_key in os.environ:
            try:
                config.weights[key] = float(os.environ[env_key])
            except ValueError:
                pass

    return config


def get_config(config_path: Optional[str] = None) -> Config:
    """
    Get the complete configuration with environment overrides.

    Args:
        config_path: Path to the configuration file.

    Returns:
        Final configuration object.
    """
    config = load_config(config_path)
    config = load_config_from_env(config)
    return config
