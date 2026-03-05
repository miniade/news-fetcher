---
name: news-fetcher
description: Fetches, processes, and clusters news articles from multiple RSS/HTML sources with deduplication and summarization
argument-hint: "[query or config options]"
user-invocable: true
license: MIT
compatibility: Requires news-fetcher Python package (pip install news-fetcher)
metadata:
  author: News Fetcher Team
  version: 0.1.3
  homepage: https://github.com/miniade/news-fetcher
  source: https://github.com/miniade/news-fetcher
  pypi: https://pypi.org/project/news-fetcher
  tags: news, rss, aggregation, summarization, clustering
---

# News Fetcher Skill

Use this skill when the user wants to:
- Fetch and aggregate news from multiple RSS feeds or HTML sources
- Remove duplicate articles covering the same story
- Group related articles into clusters/topics
- Get ranked news with diverse perspectives
- Generate summaries of top news stories

## Quick Start

### Step 1: Install the Package

```bash
pip install news-fetcher==0.1.3
```

### Step 2: Create Configuration

Create a `config.yaml` file:

```yaml
sources:
  - name: BBC News
    url: http://feeds.bbci.co.uk/news/rss.xml
    weight: 1.0
    type: rss

  - name: Reuters
    url: https://www.reutersagency.com/feed/?best-topics=tech
    weight: 1.2
    type: rss

thresholds:
  similarity: 0.8
  min_score: 0.3
  cluster_size: 2

weights:
  content: 0.6
  source: 0.2
  publish_time: 0.2
```

### Step 3: Fetch News

```bash
news-fetcher fetch --config config.yaml --limit 20
```

### Step 4: Output Results

```bash
news-fetcher fetch --config config.yaml --format markdown --output news.md
```

## Installation

**Install from PyPI (recommended):**
```bash
pip install news-fetcher==0.1.3
```

**Source & Verification:**
- PyPI: https://pypi.org/project/news-fetcher/0.1.3/
- Source: https://github.com/miniade/news-fetcher/tree/v0.1.3
- Verify integrity: `pip install news-fetcher==0.1.3 --check-hash-mode=module`

**Install from source:**
```bash
git clone https://github.com/miniade/news-fetcher.git
cd news-fetcher
pip install -e .
```

## Basic Usage

### Fetch news with default config

```bash
news-fetcher fetch --config config.yaml --limit 20
```

### Fetch specific sources

```bash
news-fetcher fetch --sources "http://feeds.bbci.co.uk/news/rss.xml" --limit 10
```

### Output as Markdown

```bash
news-fetcher fetch --config config.yaml --format markdown --output news.md
```

## Configuration

### Full Configuration Example

```yaml
sources:
  - name: BBC News
    url: http://feeds.bbci.co.uk/news/rss.xml
    weight: 1.0
    type: rss

  - name: Reuters
    url: https://www.reutersagency.com/feed/?best-topics=tech
    weight: 1.2
    type: rss

  - name: TechCrunch
    url: https://techcrunch.com/feed/
    weight: 0.9
    type: rss

thresholds:
  similarity: 0.8        # SimHash similarity threshold for duplicates
  min_score: 0.3         # Minimum article score to include
  cluster_size: 2        # Minimum articles per cluster

weights:
  content: 0.6           # Content relevance weight
  source: 0.2            # Source authority weight
  publish_time: 0.2      # Recency weight
```

### Source Types

- `rss`: RSS/Atom feeds (most common)
- `html`: HTML pages requiring extraction

### Weights and Thresholds

| Parameter | Default | Description |
|-----------|---------|-------------|
| `similarity` | 0.8 | SimHash threshold for duplicates (0-1) |
| `min_score` | 0.3 | Minimum article score to include |
| `cluster_size` | 2 | Minimum articles to form cluster |
| `content` | 0.6 | Content relevance weight |
| `source` | 0.2 | Source authority weight |
| `publish_time` | 0.2 | Recency weight |

## Advanced Options

```bash
# Fetch with diversity control
news-fetcher fetch --config config.yaml --diversity 0.7 --limit 30

# Fetch recent articles only
news-fetcher fetch --config config.yaml --since 2024-01-01T00:00:00

# Apply minimum score filter
news-fetcher fetch --config config.yaml --min-score 0.5

# Use local fixtures for testing
news-fetcher fetch --fixtures ./tests/fixtures/sample-feed.xml
```

## Configuration Management

```bash
# Validate configuration
news-fetcher config validate config.yaml

# Generate example configuration
news-fetcher config example --output example-config.yaml
```

## How It Works

### Processing Pipeline

1. **Fetch**: Retrieves articles from configured RSS/HTML sources
2. **Deduplicate**: Uses SimHash algorithm to detect near-duplicates
3. **Cluster**: Groups related articles using HDBSCAN density-based clustering
4. **Rank**: Scores articles by combining Reddit-style hotness with source authority
5. **Diversify**: Selects diverse articles using Maximal Marginal Relevance (MMR)
6. **Summarize**: Generates extractive summaries for top stories

## When to Use

Invoke this skill when:
- User asks for news aggregation: "get me the top tech news"
- User wants clustered news: "organize these news articles by topic"
- User needs news summaries: "summarize the top headlines"
- User mentions multiple news sources: "fetch news from BBC, Reuters, and CNN"
- User wants to remove duplicates: "find unique news stories from these feeds"

## Error Handling

The tool handles various error conditions:
- Network errors: Graceful fallback with cached data
- Parse errors: Skip invalid articles, continue processing
- Empty results: Return informative message
- Configuration errors: Validate before processing

## Additional Resources

For detailed technical documentation, see:
- [README.md](README.md) - Project overview and installation
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [FEATURES.md](FEATURES.md) - Feature breakdown

## Source & Provenance

- **Source Code**: https://github.com/miniade/news-fetcher
- **PyPI Package**: https://pypi.org/project/news-fetcher
- **License**: MIT
- **Current Version**: 0.1.3
