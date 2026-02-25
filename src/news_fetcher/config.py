"""
Configuration management for news-fetcher application.

This module handles loading, validation, and management of configuration
from YAML/JSON files with support for environment variable overrides.
"""

import os
from typing import Optional, Dict, Any
import yaml
from .models import Config, Source


class ConfigError(Exception):
    """Exception raised for configuration-related errors."""
    pass


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

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
    except Exception as e:
        raise ConfigError(f"Failed to parse configuration file: {e}")

    return validate_config(config_data)


def validate_config(config_data: Dict[str, Any]) -> Config:
    """
    Validate and parse configuration data.

    Args:
        config_data: Raw configuration data from file.

    Returns:
        Validated Config object.

    Raises:
        ConfigError: If configuration is invalid.
    """
    try:
        # Validate sources
        sources = []
        if "sources" in config_data:
            for source_data in config_data["sources"]:
                if "name" not in source_data or "url" not in source_data:
                    raise ConfigError("Source must have name and url fields")
                sources.append(Source(
                    name=source_data["name"],
                    url=source_data["url"],
                    weight=source_data.get("weight", 1.0),
                    type=source_data.get("type", "rss")
                ))

        # Validate thresholds
        thresholds = config_data.get("thresholds", {})
        default_thresholds = {
            "similarity": 0.8,
            "min_score": 0.5,
            "cluster_size": 2
        }
        for key, default in default_thresholds.items():
            if key not in thresholds:
                thresholds[key] = default
            else:
                thresholds[key] = float(thresholds[key])

        # Validate weights
        weights = config_data.get("weights", {})
        default_weights = {
            "content": 0.6,
            "source": 0.2,
            "publish_time": 0.2
        }
        for key, default in default_weights.items():
            if key not in weights:
                weights[key] = default
            else:
                weights[key] = float(weights[key])

        return Config(
            sources=sources,
            thresholds=thresholds,
            weights=weights
        )

    except Exception as e:
        raise ConfigError(f"Invalid configuration: {e}")


def load_config_from_env(config: Config) -> Config:
    """
    Override configuration values from environment variables.

    Args:
        config: Base configuration object.

    Returns:
        Configuration object with environment variable overrides applied.
    """
    # Example environment variable overrides:
    # NEWS_FETCHER_THRESHOLD_SIMILARITY=0.9
    # NEWS_FETCHER_WEIGHT_CONTENT=0.7

    prefix = "NEWS_FETCHER_"

    # Override thresholds
    for key in config.thresholds:
        env_key = f"{prefix}THRESHOLD_{key.upper()}"
        if env_key in os.environ:
            try:
                config.thresholds[key] = float(os.environ[env_key])
            except ValueError:
                pass

    # Override weights
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
