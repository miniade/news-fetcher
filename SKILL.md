# OpenClaw Skill: news-fetcher

## Overview

**news-fetcher** is an advanced news aggregation and clustering skill for OpenClaw. It fetches articles from multiple sources, removes duplicates, clusters related stories, ranks them by importance, and presents a diverse selection of top news stories.

## When to Use This Skill

Use **news-fetcher** when you need to:
- Aggregate news from multiple RSS feeds or HTML sources
- Remove duplicate articles covering the same story
- Group related articles into clusters/topics
- Rank articles by importance and recency
- Ensure diverse perspectives from different sources
- Generate summaries of top stories

## Configuration

### Basic Configuration

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

  - name: TechCrunch
    url: https://techcrunch.com/feed/
    weight: 0.9
    type: rss

thresholds:
  similarity: 0.8        # SimHash similarity threshold
  min_score: 0.3         # Minimum article score
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

## Usage Examples

### Basic Fetch

```bash
# Fetch with config file
news-fetcher fetch --config config.yaml --limit 20

# Fetch specific sources
news-fetcher fetch --sources "http://feeds.bbci.co.uk/news/rss.xml" --limit 10

# Output as Markdown
news-fetcher fetch --config config.yaml --format markdown --output news.md
```

### Advanced Options

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

### Configuration Management

```bash
# Validate configuration
news-fetcher config validate config.yaml

# Generate example configuration
news-fetcher config example --output example-config.yaml
```

### Self-Test

```bash
# Run self-test with fixtures
news-fetcher test --fixtures ./tests/fixtures
```

## Integration with Other Skills

### blogwatcher Skill

When `blogwatcher` is available, configure `news-fetcher` to use it for advanced article fetching:

```yaml
# config.yaml
fetching:
  use_blogwatcher: true
  blogwatcher_timeout: 30
```

Then in your workflow:
1. `blogwatcher` fetches raw articles with advanced parsing
2. `news-fetcher` processes, clusters, and ranks the articles
3. Output delivered to user

### summarize Skill

When `summarize` is available, use it for advanced abstractive summarization:

```yaml
# config.yaml
summarization:
  use_external: true
  external_skill: "summarize"
  fallback_to_extractive: true
```

Workflow:
1. `news-fetcher` clusters and ranks articles
2. For top articles, call `summarize` for abstractive summaries
3. Fallback to extractive if `summarize` unavailable
4. Present results

### Example Multi-Skill Workflow

```
User: "Get me the top tech news with summaries"

1. OpenClaw routes to news-fetcher
2. news-fetcher checks config:
   - "blogwatcher available? Use for enhanced fetching"
   - "summarize available? Use for abstractive summaries"
3. Execution:
   - blogwatcher → fetch tech sources (TechCrunch, Ars Technica, etc.)
   - news-fetcher → cluster, rank, diversify
   - summarize → generate abstractive summaries for top 5
   - news-fetcher → format and output
4. Result delivered to user
```

## Algorithm Details

### Deduplication (SimHash)

Uses Google's SimHash algorithm for near-duplicate detection:
- 64-bit fingerprint for each article
- Hamming distance <= 3 indicates duplicate
- O(n) complexity for n articles

### Clustering (HDBSCAN)

Groups related articles using HDBSCAN:
- Density-based hierarchical clustering
- Automatic noise detection
- Varying density cluster handling
- O(n²) complexity

### Ranking (Reddit Hotness + Authority)

Combines Reddit-style hotness with source authority:
```
hotness = log10(votes) + time_decay
score = source_weight * hotness * cross_source_score
```

### Diversity (MMR)

Maximal Marginal Relevance for diverse selection:
```
MMR = λ * relevance - (1-λ) * max_similarity
```

### Summarization (Extractive)

Position-aware extractive summarization:
- Weight by sentence position
- Bonus for quotes, statistics
- Select top N sentences

## Error Handling

The skill handles various error conditions:

- **Network errors**: Graceful fallback with cached data
- **Parse errors**: Skip invalid articles, continue processing
- **Empty results**: Return informative message
- **Configuration errors**: Validate before processing

## Performance Considerations

| Dataset Size | Processing Time | Memory Usage |
|--------------|-----------------|--------------|
| 100 articles | ~2 seconds | ~50 MB |
| 1,000 articles | ~15 seconds | ~200 MB |
| 10,000 articles | ~3 minutes | ~1 GB |

For large-scale processing, consider:
- Batching sources
- Incremental processing
- Distributed clustering

## Security Considerations

- Input validation on all URLs
- HTML sanitization in content
- Timeout handling for HTTP requests
- No execution of external code

## License

MIT License - See LICENSE file for details.
