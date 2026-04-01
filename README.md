# News Fetcher

[![Python 3.9+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Advanced news aggregation and clustering tool that fetches articles from multiple sources, removes duplicates, clusters related stories, ranks them by importance, and presents a diverse selection of top news stories.

## Features

- **Multi-Source Fetching**: Support for RSS/Atom feeds and HTML pages
- **Smart Deduplication**: SimHash-based near-duplicate detection
- **Intelligent Clustering**: HDBSCAN density-based clustering
- **Relevance Ranking**: Freshness + source authority scoring
- **Diverse Selection**: Source-aware final selection for multi-source feeds
- **Automatic Summarization**: Position-aware extractive summarization
- **Multiple Output Formats**: JSON, Markdown, CSV, RSS
- **Compact JSON Output**: Omits internal embeddings and centroids by default
- **GitHub Project Discovery**: Discover and rank GitHub projects worth attention today, then emit them as normal news items

## Installation

### From Source (recommended)

```bash
git clone https://github.com/miniade/news-fetcher.git
cd news-fetcher
pip install -e ".[dev]"
```

### From PyPI

```bash
pip install news-fetcher
```

> If you are validating this repository specifically, prefer installing from source so the CLI and local code stay in sync.


## Quick Start

### 1. Create a Configuration File

```yaml
# config.yaml
sources:
  - name: BBC News
    url: http://feeds.bbci.co.uk/news/rss.xml
    weight: 1.0
    type: rss
    source_type: plain_rss
    candidate_strategy: latest

  - name: Reuters
    url: https://www.reutersagency.com/feed/?best-topics=tech
    weight: 1.2
    type: rss
    source_type: plain_rss
    candidate_strategy: latest

  - name: Example HTML Source
    url: https://example.com/news
    weight: 0.9
    type: html
    source_type: generic_html
    candidate_strategy: frontpage
    selector: main article

thresholds:
  similarity: 0.8
  min_score: 0.3
  cluster_size: 2
  max_per_source: 3

weights:
  content: 0.6
  source: 0.2
  publish_time: 0.2
```

`source_type` and `candidate_strategy` are optional in v1 schema, but if you set one you must set both. The currently supported strategy vocabulary is `latest`, `frontpage`, `trending`, `curated`, `release`, `community_ranked`, `high_engagement_proxy`, `section_frontpage`, `corroboration_only`, and `project_discovery`. Supported `source_type` values also include `github_project_discovery` for GitHub project candidate acquisition. See [`docs/source-strategy-design.md`](docs/source-strategy-design.md) for the design background; this release only validates and stores the fields, it does not change fetch behavior yet.

### 1.1 GitHub project discovery example

```yaml
sources:
  - name: GitHub Trending
    url: https://github.com/trending
    weight: 1.0
    type: html
    source_type: github_project_discovery
    candidate_strategy: project_discovery

thresholds:
  similarity: 0.8
  min_score: 0.0
  cluster_size: 2
  max_per_source: 3
```

This source discovers GitHub projects from the trending surface, enriches them with repository metadata, ranks them with GitHub-specific signals, and maps selected projects into normal news items.

### 2. Fetch News

```bash
# Basic fetch
news-fetcher --config config.yaml --limit 20 run

# Write JSON to stdout
news-fetcher --config config.yaml --format json --limit 10 run > result.json

# Output as Markdown
news-fetcher --config config.yaml --format markdown --output news.md run

# Fetch with source-diverse selection
news-fetcher --config config.yaml --limit 30 run
```

> Important: global options such as `--config`, `--limit`, `--format`, `--since`, and `--min-score` must appear **before** `run`.
>
> Output behavior: a plain `news-fetcher ... run` prints the human-readable summary to stdout. If you explicitly pass `--format` without `--output`, the selected format is written to stdout instead, which makes shell redirection like `> result.json` work as expected.

### 2.1 Install and use via ClawHub skill

```bash
clawhub install news-fetcher
python3 -m venv .venv
. .venv/bin/activate
pip install "git+https://github.com/miniade/news-fetcher.git@v0.1.8"
news-fetcher version
news-fetcher config example > config.yaml
news-fetcher config validate config.yaml
news-fetcher --config config.yaml --limit 10 run
```

This path is the most reliable way to reproduce the exact `v0.1.7` release, even if PyPI has not been updated yet.

### 3. Python API

```python
from news_fetcher import NewsPipeline, Config, Source

# Create configuration
config = Config(
    sources=[
        Source(name="BBC", url="http://feeds.bbci.co.uk/news/rss.xml"),
        Source(name="Reuters", url="https://www.reutersagency.com/feed/"),
    ]
)

# Create and run pipeline
pipeline = NewsPipeline(config)
result = pipeline.run()

# Access results
for article in result.articles[:10]:
    print(f"[{article.score:.2f}] {article.title}")
```

## Command Reference

### Main Commands

```bash
# Fetch and process news
news-fetcher run [OPTIONS]

# Validate configuration
news-fetcher config validate <path>

# Generate example configuration
news-fetcher config example [OPTIONS]

# Run self-test with fixtures
news-fetcher test [OPTIONS]
```

### Global Options (place before `run`)

| Option | Description | Default |
|--------|-------------|---------|
| `--config` | Configuration file path | - |
| `--sources` | Comma-separated source URLs | - |
| `--since` | Only fetch articles after this time | - |
| `--limit` | Maximum articles to return | 50 |
| `--diversity` | MMR lambda parameter (0-1) | 0.6 |
| `--min-score` | Minimum score threshold | 0.3 |
| `--output` | Output file path | - |
| `--format` | Explicit output format for `--output` or stdout redirection (json/markdown/csv/rss) | json |
| `--fixtures` | Use local fixture files | - |
| `--verbose` | Enable verbose output | - |

## Architecture

For detailed architecture documentation, see [ARCHITECTURE.md](ARCHITECTURE.md).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              News Fetcher Pipeline                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   │
│  │  Fetch   │──▶│ Normalize│──▶│  Dedup   │──▶│ Cluster  │──▶│   Rank   │   │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘   │
│                                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐                                  │
│  │Diversify │──▶│ Summarize│──▶│  Output  │                                  │
│  └──────────┘   └──────────┘   └──────────┘                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Algorithms

| Component | Algorithm | Description |
|-----------|-----------|-------------|
| Deduplication | SimHash | 64-bit fingerprints, Hamming distance <= 3 |
| Clustering | HDBSCAN | Density-based hierarchical clustering |
| Ranking | Freshness + source weighting | Time decay + configured source authority |
| Diversity | Source-aware selection | Balanced final selection with per-source caps |
| Summarization | Position-based | Extractive with position weighting |

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=news_fetcher --cov-report=html

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m e2e

# Run with verbose output
pytest -v
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Format code
black src tests
isort src tests

# Run type checking
mypy src

# Run linting
flake8 src tests
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and ensure coverage is maintained
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- SimHash algorithm based on [Charikar's SimHash](https://www.cs.princeton.edu/courses/archive/spring04/cos598B/bib/CharikarEstim.pdf)
- HDBSCAN clustering from [scikit-learn-contrib/hdbscan](https://github.com/scikit-learn-contrib/hdbscan)
- Reddit hotness algorithm from [How Reddit Ranking Algorithms Work](https://medium.com/hacking-and-gonzo/how-reddit-ranking-algorithms-work-ef111e33d0d9)
- MMR algorithm from [Carbonell and Goldstein (1998)](https://www.cs.cmu.edu/~jgc/publication/The_Use_of_MMR_Diversity_Based_LTMIR_1998.pdf)
