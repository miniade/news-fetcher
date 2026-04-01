# News Fetcher - Feature Summary

## Overview

**News Fetcher** is an advanced news aggregation and clustering tool built with Python. It implements state-of-the-art algorithms for fetching, deduplicating, clustering, ranking, and presenting news articles from multiple sources.

## Implemented Features

### Core Functionality ✓

1. **Multi-Source Fetching**
   - RSS/Atom feed parsing
   - HTML page extraction
   - Support for multiple concurrent sources
   - Time-based filtering

2. **Article Normalization**
   - HTML tag removal
   - Whitespace normalization
   - URL normalization
   - Date extraction and parsing
   - Exact duplicate removal

3. **Near-Duplicate Detection (SimHash)**
   - 64-bit fingerprint generation
   - Hamming distance comparison
   - Configurable threshold (default: 3 bits)
   - O(n) complexity for n articles

4. **Article Clustering (HDBSCAN)**
   - Density-based hierarchical clustering
   - Automatic noise detection
   - TF-IDF vectorization
   - Configurable minimum cluster size

5. **Relevance Ranking (Reddit Hotness + Authority)**
   - Reddit-style hotness algorithm
   - Exponential time decay
   - Source authority weighting
   - Cross-source coverage scoring

6. **Diversity Selection (MMR)**
   - Maximal Marginal Relevance algorithm
   - Configurable relevance-diversity tradeoff (λ = 0.6)
   - Greedy iterative selection
   - O(k × n²) complexity

7. **Extractive Summarization**
   - Position-based sentence extraction
   - Title and lead paragraph weighting
   - Quote and statistic detection
   - Configurable summary length

8. **Multiple Output Formats**
   - JSON with full metadata
   - Markdown for human reading
   - CSV for data analysis
   - RSS 2.0 for syndication

9. **GitHub Project Discovery**
   - GitHub Trending candidate acquisition
   - Repository metadata enrichment via GitHub API
   - Rule-based project ranking with structured reasons
   - Mapping ranked projects into normal news items
   - Conservative pipeline cap to avoid flooding the digest

### Command-Line Interface ✓

The CLI provides comprehensive control:

```bash
# Fetch with config
news-fetcher --config config.yaml --limit 20 run

# Output as Markdown
news-fetcher --format markdown --output news.md run

# Diversity control
news-fetcher --diversity 0.7 --limit 30 run

# Validate config
news-fetcher config validate config.yaml

# Generate example config
news-fetcher config example > example.yaml

# Run self-test
news-fetcher --fixtures ./tests/fixtures run
```

### Python API ✓

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

## Algorithm Implementations

### SimHash Deduplication
- **Purpose**: Detect near-duplicate articles
- **Algorithm**: 64-bit locality-sensitive hashing
- **Comparison**: Hamming distance with threshold (default: 3)
- **Complexity**: O(n) for n articles

### HDBSCAN Clustering
- **Purpose**: Group related articles
- **Algorithm**: Hierarchical Density-Based Spatial Clustering
- **Parameters**: min_cluster_size (default: 2)
- **Complexity**: O(n²) for n articles

### Reddit Hotness Ranking
- **Purpose**: Rank by importance
- **Algorithm**: log(votes) + time_decay
- **Formula**: score = log10(votes) * sign + seconds/gravity
- **Factors**: Cluster size, source authority, recency

### MMR Diversity Selection
- **Purpose**: Ensure diverse results
- **Algorithm**: Maximal Marginal Relevance
- **Formula**: MMR = λ*relevance - (1-λ)*max(similarity)
- **Complexity**: O(k × n²) for k selections from n articles

### Position-Based Summarization
- **Purpose**: Generate article summaries
- **Algorithm**: Position-aware extractive
- **Weights**: Title > Lead > Quotes > Stats > Body
- **Output**: Top N sentences

## Testing

The project includes comprehensive tests:

```bash
# Run all tests
pytest

# With coverage
pytest --cov=news_fetcher --cov-report=html

# Specific test types
pytest -m unit
pytest -m integration
pytest -m e2e
```

Current test files:
- `test_dedup.py` - SimHash deduplication tests
- `test_diversify.py` - MMR diversity tests
- `test_fetch.py` - Fetching tests
- `test_normalize.py` - Normalization tests
- `test_cluster.py` - Clustering tests
- `test_rank.py` - Ranking tests
- `test_summarize.py` - Summarization tests
- `test_output.py` - Output format tests
- `test_cli.py` - CLI tests
- `test_e2e.py` - End-to-end tests
- `test_github_enrich.py` - GitHub enrichment tests
- `test_github_rank.py` - GitHub ranking tests
- `test_github_map.py` - GitHub mapping tests

## Documentation

Comprehensive documentation is included:

- `README.md` - Overview, installation, quick start
- `ARCHITECTURE.md` - Detailed architecture and algorithms
- `SKILL.md` - OpenClaw skill documentation
- `FEATURES.md` - This feature summary
- `research.md` - Algorithm research and comparisons

## Performance

| Articles | Processing Time | Memory |
|----------|-----------------|--------|
| 100 | ~2 seconds | ~50 MB |
| 1,000 | ~15 seconds | ~200 MB |
| 10,000 | ~3 minutes | ~1 GB |

## Future Enhancements

Potential improvements:

1. **Real-time Streaming**: Kafka integration
2. **Machine Learning**: Neural ranking, abstractive summarization
3. **User Personalization**: Collaborative filtering
4. **Graph Analysis**: Knowledge graphs
5. **Distributed Processing**: Spark/Dask
6. **Advanced NLP**: NER, sentiment analysis, topic modeling

## License

MIT License - See LICENSE file for details.
