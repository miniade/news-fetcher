"""Tests for config validation and loading."""

import pytest

from news_fetcher.config import ConfigError, load_config, validate_config


class TestConfig:
    def test_validate_config_accepts_mapping(self):
        config = validate_config(
            {
                "sources": [
                    {
                        "name": "Python Insider",
                        "url": "https://feeds.feedburner.com/PythonInsider",
                        "type": "rss",
                        "source_type": "official_blog",
                        "candidate_strategy": "release",
                    },
                    {
                        "name": "Example HTML",
                        "url": "https://example.com/news",
                        "type": "html",
                        "source_type": "generic_html",
                        "candidate_strategy": "frontpage",
                        "selector": "main article",
                    },
                ],
                "thresholds": {"similarity": 0.8},
                "weights": {"content": 0.6},
            }
        )

        assert len(config.sources) == 2
        assert config.sources[0].source_type == "official_blog"
        assert config.sources[0].candidate_strategy == "release"
        assert config.sources[1].selector == "main article"
        assert config.sources[1].source_type == "generic_html"
        assert config.sources[1].candidate_strategy == "frontpage"
        assert config.thresholds["max_per_source"] == 3
        assert config.thresholds["weak_source_max_per_source"] == 1
        assert config.thresholds["corroboration_min_sources"] == 2
        assert config.thresholds["min_score"] == 0.3

    def test_validate_config_parses_source_acquisition_controls(self):
        config = validate_config(
            {
                "sources": [
                    {
                        "name": "Example",
                        "url": "https://example.com/feed.xml",
                        "type": "rss",
                        "source_type": "plain_rss",
                        "candidate_strategy": "latest",
                        "acquisition": {
                            "weak_source": True,
                            "weak_source_weight_multiplier": 0.4,
                            "contribution_limit": 1,
                            "recency_window_hours": 12,
                        },
                    }
                ]
            }
        )

        source = config.sources[0]
        assert source.weak_source is True
        assert source.weak_source_weight_multiplier == 0.4
        assert source.contribution_limit == 1
        assert source.recency_window_hours == 12.0

    def test_load_config_from_path(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
sources:
  - name: Example
    url: https://example.com/feed.xml
    source_type: plain_rss
    candidate_strategy: latest
  - name: Example HTML
    url: https://example.com/news
    type: html
    source_type: curated_editorial
    candidate_strategy: curated
    selector: main article
thresholds:
  similarity: 0.9
  min_score: 0.25
  max_per_source: 2
weights:
  content: 0.7
""".strip()
        )

        config = load_config(str(config_file))

        assert config.thresholds["similarity"] == 0.9
        assert config.thresholds["min_score"] == 0.25
        assert config.thresholds["max_per_source"] == 2
        assert config.weights["content"] == 0.7
        assert config.sources[0].source_type == "plain_rss"
        assert config.sources[0].candidate_strategy == "latest"
        assert config.sources[1].selector == "main article"
        assert config.sources[1].source_type == "curated_editorial"
        assert config.sources[1].candidate_strategy == "curated"

    def test_validate_config_rejects_partial_source_strategy_fields(self):
        with pytest.raises(
            ConfigError, match="source_type and candidate_strategy must be set together"
        ):
            validate_config(
                {
                    "sources": [
                        {
                            "name": "Example",
                            "url": "https://example.com/feed.xml",
                            "source_type": "plain_rss",
                        }
                    ]
                }
            )

    def test_validate_config_rejects_candidate_strategy_without_source_type(self):
        with pytest.raises(
            ConfigError, match="source_type and candidate_strategy must be set together"
        ):
            validate_config(
                {
                    "sources": [
                        {
                            "name": "Example",
                            "url": "https://example.com/feed.xml",
                            "candidate_strategy": "latest",
                        }
                    ]
                }
            )

    def test_validate_config_rejects_unknown_candidate_strategy(self):
        with pytest.raises(ConfigError, match="Unsupported candidate_strategy 'editor_picks'"):
            validate_config(
                {
                    "sources": [
                        {
                            "name": "Example",
                            "url": "https://example.com/feed.xml",
                            "source_type": "plain_rss",
                            "candidate_strategy": "editor_picks",
                        }
                    ]
                }
            )

    def test_supported_source_strategy_vocab_stays_in_sync(self):
        from news_fetcher.config import (
            SUPPORTED_CANDIDATE_STRATEGIES,
            SUPPORTED_CANDIDATE_STRATEGIES_BY_SOURCE_TYPE,
            SUPPORTED_SOURCE_TYPES,
            SUPPORTED_SOURCE_TYPES_BY_FETCH_TYPE,
        )

        assert set(SUPPORTED_SOURCE_TYPES_BY_FETCH_TYPE) == {"rss", "html"}
        assert set().union(*SUPPORTED_SOURCE_TYPES_BY_FETCH_TYPE.values()) == SUPPORTED_SOURCE_TYPES
        assert (
            set().union(*SUPPORTED_CANDIDATE_STRATEGIES_BY_SOURCE_TYPE.values())
            == SUPPORTED_CANDIDATE_STRATEGIES
        )

    def test_validate_config_rejects_invalid_source_type_for_fetch_type(self):
        with pytest.raises(ConfigError, match="does not support source_type 'community_ranked'"):
            validate_config(
                {
                    "sources": [
                        {
                            "name": "Example RSS",
                            "url": "https://example.com/feed.xml",
                            "type": "rss",
                            "source_type": "community_ranked",
                            "candidate_strategy": "community_ranked",
                        }
                    ]
                }
            )

    def test_validate_config_rejects_invalid_strategy_for_source_type(self):
        with pytest.raises(ConfigError, match="does not support candidate_strategy 'release'"):
            validate_config(
                {
                    "sources": [
                        {
                            "name": "Example Community",
                            "url": "https://example.com/",
                            "type": "html",
                            "source_type": "community_ranked",
                            "candidate_strategy": "release",
                        }
                    ]
                }
            )


    def test_validate_config_accepts_github_project_discovery_source(self):
        config = validate_config(
            {
                "sources": [
                    {
                        "name": "GitHub Trending Projects",
                        "url": "https://github.com/trending",
                        "type": "html",
                        "source_type": "github_project_discovery",
                        "candidate_strategy": "project_discovery",
                    }
                ]
            }
        )

        assert config.sources[0].source_type == "github_project_discovery"
        assert config.sources[0].candidate_strategy == "project_discovery"
