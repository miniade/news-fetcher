"""Tests for config validation and loading."""

from news_fetcher.config import load_config, validate_config


class TestConfig:
    def test_validate_config_accepts_mapping(self):
        config = validate_config(
            {
                "sources": [{"name": "Example", "url": "https://example.com/feed.xml"}],
                "thresholds": {"similarity": 0.8},
                "weights": {"content": 0.6},
            }
        )

        assert len(config.sources) == 1
        assert config.thresholds["max_per_source"] == 3

    def test_load_config_from_path(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
sources:
  - name: Example
    url: https://example.com/feed.xml
thresholds:
  similarity: 0.9
  max_per_source: 2
weights:
  content: 0.7
""".strip()
        )

        config = load_config(str(config_file))

        assert config.thresholds["similarity"] == 0.9
        assert config.thresholds["max_per_source"] == 2
        assert config.weights["content"] == 0.7
