"""Tests for the CLI module."""

import json
import re
from datetime import datetime
from pathlib import Path

from click.testing import CliRunner

from news_fetcher import __version__
from news_fetcher.cli import main
from news_fetcher.config import load_config
from news_fetcher.models import Article


def _read_project_version() -> str:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    match = re.search(
        r"^version\s*=\s*['\"]([^'\"]+)['\"]\s*$",
        pyproject.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    assert match is not None
    return match.group(1)


def _result_with_article(title: str = "t"):
    return type(
        "Result",
        (),
        {
            "articles": [
                Article(
                    id="1",
                    title=title,
                    content="c",
                    url="https://example.com/story",
                    source="Example",
                    published_at=datetime(2026, 3, 12),
                    score=0.5,
                )
            ],
            "clusters": [],
        },
    )()


class TestCLI:
    """Test class for the CLI."""

    def test_cli_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "News Fetcher" in result.output

    def test_cli_config_loading(self):
        config = load_config("config.yaml")
        assert config is not None

    def test_cli_version_matches_project_version(self):
        project_version = _read_project_version()

        runner = CliRunner()
        result = runner.invoke(main, ["version"])
        assert result.exit_code == 0
        assert project_version in result.output
        assert __version__ == project_version

    def test_cli_config_validate_accepts_path(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
sources:
  - name: Example
    url: https://example.com/feed.xml
thresholds:
  similarity: 0.8
weights:
  content: 0.6
""".strip()
        )

        runner = CliRunner()
        result = runner.invoke(main, ["config", "validate", str(config_file)])
        assert result.exit_code == 0
        assert "Configuration file is valid" in result.output

    def test_cli_run_passes_since_diversity_and_default_min_score_without_config(self, monkeypatch):
        calls = {}

        class FakePipeline:
            def __init__(self):
                self.diversity_selector = type("Selector", (), {"lambda_param": None})()
                self.config = type("Config", (), {"thresholds": {"min_score": 0.5}})()

            def run(self, sources=None, since=None, limit=None):
                calls["sources"] = sources
                calls["since"] = since
                calls["limit"] = limit
                calls["diversity"] = self.diversity_selector.lambda_param
                calls["min_score"] = self.config.thresholds["min_score"]
                return _result_with_article()

        monkeypatch.setattr(
            "news_fetcher.cli.create_default_pipeline",
            lambda *_args, **_kwargs: FakePipeline(),
        )

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "--since",
                "2026-03-12T00:00:00",
                "--diversity",
                "0.75",
                "--limit",
                "7",
                "run",
            ],
        )

        assert result.exit_code == 0
        assert calls["since"] == datetime(2026, 3, 12, 0, 0)
        assert calls["limit"] == 7
        assert calls["diversity"] == 0.75
        assert calls["min_score"] == 0.3

    def test_cli_run_respects_config_min_score_by_default(self, monkeypatch, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
sources:
  - name: Example
    url: https://example.com/feed.xml
thresholds:
  min_score: 0.55
""".strip()
        )
        calls = {}

        class FakePipeline:
            def __init__(self):
                self.diversity_selector = type("Selector", (), {"lambda_param": None})()
                self.config = type("Config", (), {"thresholds": {"min_score": 0.55}})()

            def run(self, sources=None, since=None, limit=None):
                calls["min_score"] = self.config.thresholds["min_score"]
                return _result_with_article()

        monkeypatch.setattr(
            "news_fetcher.cli.create_default_pipeline",
            lambda *_args, **_kwargs: FakePipeline(),
        )

        runner = CliRunner()
        result = runner.invoke(main, ["--config", str(config_file), "run"])

        assert result.exit_code == 0
        assert calls["min_score"] == 0.55

    def test_cli_run_overrides_min_score_when_explicit(self, monkeypatch, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
sources:
  - name: Example
    url: https://example.com/feed.xml
thresholds:
  min_score: 0.55
""".strip()
        )
        calls = {}

        class FakePipeline:
            def __init__(self):
                self.diversity_selector = type("Selector", (), {"lambda_param": None})()
                self.config = type("Config", (), {"thresholds": {"min_score": 0.55}})()

            def run(self, sources=None, since=None, limit=None):
                calls["min_score"] = self.config.thresholds["min_score"]
                return _result_with_article()

        monkeypatch.setattr(
            "news_fetcher.cli.create_default_pipeline",
            lambda *_args, **_kwargs: FakePipeline(),
        )

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--config", str(config_file), "--min-score", "0.42", "run"],
        )

        assert result.exit_code == 0
        assert calls["min_score"] == 0.42

    def test_cli_run_writes_output_file(self, monkeypatch, tmp_path):
        class FakePipeline:
            def __init__(self):
                self.diversity_selector = type("Selector", (), {"lambda_param": None})()
                self.config = type("Config", (), {"thresholds": {"min_score": 0.3}})()

            def run(self, sources=None, since=None, limit=None):
                return _result_with_article("saved article")

        monkeypatch.setattr(
            "news_fetcher.cli.create_default_pipeline",
            lambda *_args, **_kwargs: FakePipeline(),
        )

        output_path = tmp_path / "out" / "news.json"
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "--output",
                str(output_path),
                "--format",
                "json",
                "run",
            ],
        )

        assert result.exit_code == 0
        assert output_path.exists()
        parsed = json.loads(output_path.read_text(encoding="utf-8"))
        assert parsed["articles"][0]["title"] == "saved article"
        assert "Wrote 1 articles" in result.output
