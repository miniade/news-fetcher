# News Fetcher Architecture

## Overview

News Fetcher is a Python-based news aggregation and clustering tool that fetches articles from multiple sources, removes duplicates, clusters related stories, ranks them by importance, and presents a diverse selection of top news stories.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              News Fetcher Pipeline                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐ │
│  │  Fetch   │──▶│ Normalize│──▶│  Dedup   │──▶│ Cluster  │──▶│   Rank   │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘ │
│                                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐                                 │
│  │Diversify │──▶│ Summarize│──▶│  Output  │                                 │
│  └──────────┘   └──────────┘   └──────────┘                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Module Descriptions

### 1. Fetch Module (`fetch.py`)

**Purpose**: Fetch articles from various news sources (RSS, HTML).

**Key Components**:
- `fetch_rss()`: Parse RSS/Atom feeds using feedparser
- `fetch_html()`: Extract articles from HTML pages using BeautifulSoup
- `fetch_all()`: Fetch from multiple sources concurrently
- `should_fetch()`: Check if source needs fetching based on last fetch time

**Input**: List of Source objects with URLs and types
**Output**: List of raw Article objects

### 2. Normalize Module (`normalize.py`)

**Purpose**: Clean and standardize article content.

**Key Components**:
- `normalize_article()`: Normalize a single article
- `normalize_text()`: Clean text content (HTML removal, whitespace normalization)
- `normalize_title()`: Clean and standardize titles
- `normalize_url()`: Normalize and validate URLs
- `extract_published_date()`: Extract and parse publication dates
- `dedupe_articles()`: Remove exact duplicates by URL/title

**Input**: Raw Article objects
**Output**: Normalized Article objects

### 3. Deduplication Module (`dedup.py`)

**Purpose**: Detect and remove near-duplicate articles using SimHash.

**Key Components**:
- `SimHash`: 64-bit fingerprint generation for text
  - `compute()`: Generate SimHash fingerprint
  - `distance()`: Calculate Hamming distance between hashes
  - `_tokenize()`: Weighted tokenization using TF-IDF-like weights
- `Deduplicator`: Main deduplication interface
  - `is_duplicate()`: Check if two hashes are duplicates (Hamming distance <= threshold)
  - `find_duplicates()`: Find all duplicate groups in a list
  - `add_document()`: Add document and check for duplicates

**Algorithm**: SimHash with Hamming distance threshold (default: 3)
**Complexity**: O(n) for n articles

**Input**: List of normalized Article objects
**Output**: Deduplicated list of Article objects

### 4. Clustering Module (`cluster.py`)

**Purpose**: Group related articles into clusters using HDBSCAN.

**Key Components**:
- `ArticleClusterer`: Main clustering interface
  - `fit()`: Cluster articles and return clusters
  - `partial_fit()`: Online clustering for streaming articles
  - `_compute_embeddings()`: Compute TF-IDF vectors
- `ClusterManager`: Manage cluster lifecycle
  - `add_cluster()`: Add new cluster
  - `update_cluster()`: Add article to cluster
  - `merge_clusters()`: Merge two clusters
  - `get_all_clusters()`: Get all clusters

**Algorithm**: HDBSCAN (Hierarchical Density-Based Spatial Clustering)
- `min_cluster_size`: Minimum articles per cluster (default: 2)
- `min_samples`: Core point threshold (default: 1)

**Input**: List of deduplicated Article objects
**Output**: Tuple of (List[Article], List[Cluster]) - articles with cluster_id assigned

### 5. Ranking Module (`rank.py`)

**Purpose**: Rank articles by importance using Reddit-style hotness + source authority.

**Key Components**:
- `ArticleRanker`: Main ranking interface
  - `rank()`: Rank articles and return sorted list
  - `_calculate_score()`: Calculate composite score
  - `_calculate_hotness()`: Calculate Reddit-style hotness
  - `_calculate_time_decay()`: Calculate time decay factor
  - `_get_source_weight()`: Get source authority weight

**Algorithms**:

1. **Reddit Hotness**:
   ```
   score = log10(max(abs(net_votes), 1)) * sign(net_votes) + (time_seconds / gravity)
   ```
   - `gravity`: Decay speed (default: 1.8)
   - Uses cluster size as proxy for "votes"

2. **Time Decay**:
   ```
   decay = exp(-ln(2) * age_seconds / half_life)
   ```
   - `half_life`: Decay rate (default: 3600 seconds)

3. **Source Authority**:
   ```
   weight = base_weight + domain_reputation
   ```

4. **Cross-Source Score**:
   ```
   score = (1 + log(cluster_size)) * (unique_sources / cluster_size)
   ```

5. **Final Composite Score**:
   ```
   score = source_weight * hotness * cross_source_score * content_quality
   ```

**Input**: List of clustered Article objects, List of Cluster objects
**Output**: Sorted list of Article objects (by score, descending)

### 6. Diversity Module (`diversify.py`)

**Purpose**: Select diverse articles using Maximal Marginal Relevance (MMR).

**Key Components**:
- `DiversitySelector`: Main diversity selection interface
  - `select()`: Select k diverse articles using MMR
  - `_compute_similarity_matrix()`: Compute pairwise similarity
  - `_compute_mmr_score()`: Calculate MMR score
- `mmr_select()`: Pure MMR implementation
- `greedy_diversity_select()`: Greedy diversity alternative
- `balance_sources()`: Ensure source diversity

**Algorithm**: Maximal Marginal Relevance (MMR)
```
MMR = λ * relevance - (1-λ) * max(similarity to selected)
```
- `λ` (lambda): Relevance-diversity tradeoff (default: 0.6)
  - λ = 1: Maximum relevance, no diversity
  - λ = 0: Maximum diversity, no relevance
- Selection: Greedy iterative selection of highest MMR score

**Complexity**: O(k * n^2) where k = selected count, n = candidate count

**Input**: Ranked list of Article objects, integer k (number to select)
**Output**: List of k diverse Article objects

### 7. Summarization Module (`summarize.py`)

**Purpose**: Generate article summaries using extractive methods.

**Key Components**:
- `ArticleSummarizer`: Main summarization interface
  - `summarize()`: Generate summary for article
  - `summarize_text()`: Generate summary from raw text
  - `extract_key_sentences()`: Extract top N important sentences
- `position_based_summary()`: Abridge-style position-aware
- `textrank_summary()`: TextRank graph-based
- `lead_n_summary()`: Simple lead-N approach
- `centroid_summary()`: Centroid-based for clusters

**Algorithms**:

1. **Position-Based (Abridge-style)**:
   - Weight sentences by position: title > first para > quotes > stats > last para
   - Score = position_weight * type_bonus
   - Select top N by score

2. **TextRank**:
   - Tokenize into sentences
   - Build similarity matrix (cosine similarity of TF-IDF vectors)
   - Apply PageRank algorithm
   - Select top N by PageRank score

3. **Lead-N**:
   - Extract first N sentences
   - Fast fallback method

**Input**: Article objects or raw text
**Output**: Summary string (plain text)

### 8. Output Module (`output.py`)

**Purpose**: Format and output processed articles in various formats.

**Key Components**:
- `OutputFormatter`: Main output interface
  - `format()`: Format articles for output
  - `save()`: Save to file
- `format_json()`: JSON output with metadata
- `format_markdown()`: Human-readable Markdown
- `format_csv()`: CSV for data analysis
- `format_rss()`: RSS 2.0 feed output

**Output Formats**:

1. **JSON**:
   ```json
   {
     "metadata": {
       "generated_at": "2024-01-15T10:30:00Z",
       "total_articles": 50,
       "total_clusters": 12
     },
     "clusters": [...],
     "articles": [...]
   }
   ```

2. **Markdown**:
   ```markdown
   # News Digest
   ### [Article Title](url)
   **Source**: BBC | **Published**: 2 hours ago
   **Summary**: Brief summary...
   ```

3. **CSV**:
   - Columns: title, url, source, published_at, score, summary

4. **RSS**:
   - Standard RSS 2.0 format with all article metadata

**Input**: List of Article objects, List of Cluster objects
**Output**: Formatted string in chosen format

### 9. Pipeline Module (`pipeline.py`)

**Purpose**: Orchestrate the entire news processing pipeline.

**Key Components**:
- `NewsPipeline`: Main pipeline class
  - `run()`: Run full pipeline with live sources
  - `run_from_fixtures()`: Run with local fixture files
  - Stage methods: `_fetch()`, `_normalize()`, `_deduplicate()`, `_cluster()`, `_rank()`, `_diversify()`, `_summarize()`, `_output()`
- `PipelineResult`: Result container with articles, clusters, metadata
- `create_default_pipeline()`: Factory function

**Pipeline Flow**:
```
Sources → Fetch → Normalize → Deduplicate → Cluster → Rank → Diversify → Summarize → Output
```

**Configuration**:
- Sources: List of RSS/HTML sources with weights
- Thresholds: Similarity, min score, cluster size
- Weights: Content, source, time weighting

**Input**: Config object, optional source list, optional time filter
**Output**: PipelineResult with processed articles and clusters

### 10. CLI Module (`cli.py`)

**Purpose**: Command-line interface for the news-fetcher tool.

**Key Components**:
- `cli`: Main Click group
- `run`: Main command for fetching and processing news
- `config`: Configuration management subcommands (validate, example)
- `test`: Self-test with fixtures

**Commands**:

1. **run** (main command):
   ```bash
   news-fetcher --sources "http://..." --limit 50 --format markdown run
   ```
   Options: --sources, --since, --limit, --diversity, --min-score, --output, --format, --fixtures

2. **config validate**:
   ```bash
   news-fetcher config validate config.yaml
   ```

3. **config example**:
   ```bash
   news-fetcher config example > example.yaml
   ```

4. **test**:
   ```bash
   news-fetcher test --fixtures ./tests/fixtures
   ```

**Input**: Command-line arguments
**Output**: Formatted news output or status messages

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Data Flow Diagram                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Sources                    Processing                         Output       │
│   ───────                    ─────────                         ──────       │
│                                                                              │
│   ┌─────────┐              ┌─────────────┐                    ┌─────────┐   │
│   │RSS Feeds│─────────────▶│   Fetch     │───────────────────▶│  JSON   │   │
│   └─────────┘              └─────────────┘                    └─────────┘   │
│         │                           │                              │         │
│   ┌─────────┐              ┌─────────────┐                    ┌─────────┐   │
│   │HTML     │─────────────▶│  Normalize  │───────────────────▶│Markdown │   │
│   │Pages    │              └─────────────┘                    └─────────┘   │
│   └─────────┘                      │                              │         │
│                              ┌─────────────┐                    ┌─────────┐   │
│                              │   Dedup     │───────────────────▶│  CSV    │   │
│                              │  (SimHash)  │                    └─────────┘   │
│                              └─────────────┘                                  │
│                                       │                                         │
│                              ┌─────────────┐                                    │
│                              │   Cluster   │                                    │
│                              │  (HDBSCAN)  │                                    │
│                              └─────────────┘                                    │
│                                       │                                         │
│                              ┌─────────────┐                                    │
│                              │    Rank     │                                    │
│                              │  (Hotness)  │                                    │
│                              └─────────────┘                                    │
│                                       │                                         │
│                              ┌─────────────┐                                    │
│                              │  Diversify  │                                    │
│                              │   (MMR)     │                                    │
│                              └─────────────┘                                    │
│                                       │                                         │
│                              ┌─────────────┐                                    │
│                              │  Summarize  │                                    │
│                              │(Extractive) │                                    │
│                              └─────────────┘                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Algorithm Details

### SimHash Deduplication

SimHash creates a 64-bit fingerprint for each article. Two articles are considered duplicates if their Hamming distance is <= 3.

**Process**:
1. Tokenize text into words with TF-IDF weights
2. Compute hash for each token
3. Combine weighted hashes into 64-bit fingerprint
4. Compare fingerprints using Hamming distance

### HDBSCAN Clustering

HDBSCAN groups similar articles into clusters based on density.

**Parameters**:
- `min_cluster_size`: Minimum articles per cluster (default: 2)
- `min_samples`: Core point threshold (default: 1)

**Process**:
1. Compute TF-IDF vectors for articles
2. Apply HDBSCAN to find density-based clusters
3. Assign cluster IDs to articles
4. Compute cluster centroids and representative articles

### Reddit-Style Hotness Ranking

Combines time decay with engagement metrics.

**Formula**:
```
hotness = log10(max(abs(votes), 1)) * sign(votes) + (seconds / gravity)
```

Where:
- `votes`: Cluster size (proxy for engagement)
- `seconds`: Article age in seconds
- `gravity`: Decay speed (default: 45000 seconds ~ 12.5 hours)

**Final Score**:
```
score = source_weight * hotness * cross_source_score * content_quality
```

### Maximal Marginal Relevance (MMR)

Balances relevance with diversity.

**Formula**:
```
MMR = λ * relevance - (1-λ) * max(similarity to selected)
```

Where:
- `λ`: Relevance-diversity tradeoff (default: 0.6)
- `relevance`: Article ranking score
- `similarity`: Cosine similarity between article embeddings

**Process**:
1. Initialize selected set with highest-ranked article
2. For remaining positions, select article with highest MMR score
3. Repeat until k articles selected

**Complexity**: O(k * n²) where k = selected, n = candidates

### Extractive Summarization

Generates summaries by extracting key sentences.

**Position-Based Method** (default):
1. Weight sentences by position importance
2. Bonus for quotes ("..."), statistics (numbers), named entities
3. Score = position_weight × type_bonus
4. Select top N sentences, preserving order

**TextRank Method** (alternative):
1. Build sentence similarity matrix
2. Apply PageRank algorithm
3. Select top N sentences by PageRank score

## Data Models

### Article
```python
@dataclass
class Article:
    id: str                          # Unique identifier
    title: str                       # Article title
    content: str                     # Full content
    url: str                         # Original URL
    source: str                      # Source name
    published_at: datetime           # Publication time
    fetched_at: datetime             # Fetch time
    author: Optional[str]          # Author name
    summary: Optional[str]          # Generated summary
    embeddings: Optional[List[float]]  # Vector embeddings
    cluster_id: Optional[str]       # Assigned cluster
    score: float                    # Importance score
```

### Cluster
```python
@dataclass
class Cluster:
    id: str                         # Unique identifier
    articles: List[Article]        # Articles in cluster
    centroid: Optional[List[float]]  # Cluster centroid
    representative_article: Optional[Article]  # Most representative
```

### Source
```python
@dataclass
class Source:
    name: str                       # Source name
    url: str                        # Feed URL
    weight: float                   # Authority weight
    type: str                       # "rss" or "html"
```

### Config
```python
@dataclass
class Config:
    sources: List[Source]                  # News sources
    thresholds: Dict[str, float]            # Similarity, score, cluster size
    weights: Dict[str, float]               # Content, source, time weights
```

## Performance Characteristics

| Module | Time Complexity | Space Complexity | Notes |
|--------|-----------------|------------------|-------|
| Fetch | O(s × n) | O(n) | s = sources, n = articles per source |
| Normalize | O(n × L) | O(n) | L = average text length |
| Deduplication | O(n × k) | O(n) | k = hash size (64 bits) |
| Clustering | O(n²) | O(n²) | HDBSCAN with TF-IDF |
| Ranking | O(n log n) | O(n) | Sorting by score |
| Diversity | O(k × n²) | O(n²) | MMR selection |
| Summarization | O(n × L²) | O(n) | Position-based extraction |

**Overall Pipeline**: O(n²) dominated by clustering and diversity selection

## Error Handling

All modules use custom exceptions defined in `exceptions.py`:

- `NewsFetcherError`: Base exception
- `FetchError`: Network/fetch failures
- `ParseError`: Content parsing failures
- `ConfigError`: Configuration errors
- `ProcessingError`: General processing errors
- `SourceError`: Source-specific errors

## Extension Points

The architecture supports extension through:

1. **Custom Fetchers**: Implement new fetchers by adding methods to `fetch.py`
2. **Custom Rankers**: Extend `ArticleRanker` with new scoring algorithms
3. **Custom Output Formats**: Add format methods to `output.py`
4. **Custom Clustering**: Replace HDBSCAN with alternative algorithms
5. **Plugin System**: Future support for external plugins

## Future Enhancements

Potential improvements for future versions:

1. **Real-time Streaming**: Kafka integration for live news streams
2. **Machine Learning**: Neural ranking models, abstractive summarization
3. **User Personalization**: Collaborative filtering, user profiles
4. **Graph Analysis**: Knowledge graphs, entity relationships
5. **Distributed Processing**: Spark/Dask for large-scale processing
6. **Advanced NLP**: Named entity recognition, sentiment analysis, topic modeling
