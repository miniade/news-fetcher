# News Aggregation Algorithms Research

## Executive Summary

This research report analyzes existing news aggregation tools and algorithms to guide the implementation of `news-fetcher` - a modern news aggregation system. Key findings include:

1. **Existing Tools**: NewsBlur and Feedly are the most popular cloud-based aggregators, with tt-rss as the leading self-hosted option. All tools focus on RSS/Atom feed parsing, deduplication, and customization, but NewsBlur stands out with its machine learning-based personalization.

2. **Deduplication**: SimHash is the top choice for large-scale deduplication due to its high performance and accuracy. It creates compact fingerprints that enable fast Hamming distance comparisons.

3. **Clustering**: HDBSCAN provides superior clustering quality for news articles by handling varying densities and noise. For streaming news, online hierarchical clustering offers real-time performance.

4. **Ranking**: Reddit's hotness algorithm balances recency and engagement effectively. Combined with source authority weighting (PageRank-style), it provides a robust ranking system.

5. **Diversity Selection**: Maximal Marginal Relevance (MMR) strikes the best balance between relevance and diversity, ensuring users see both important and varied content.

6. **Summarization**: Abridge-style position-aware extractive summarization provides high-quality, concise summaries that maintain article coherence and key information.

## 1. Existing RSS Aggregators/News Tools

| Tool | Type | Architecture | Key Features | Strengths | Weaknesses |
|------|------|--------------|--------------|-----------|------------|
| **NewsBlur** | Cloud | Python/Django backend, PostgreSQL, Redis for caching | - Machine learning-based personalization<br>- Social news discovery<br>- Advanced filtering (tags, keywords)<br>- Extractive summarization | - Excellent deduplication<br>- Strong personalization<br>- Active community | - Complex UI for beginners<br>- Limited free plan |
| **Feedly** | Cloud | Cloud-hosted, scalable backend | - AI-powered content discovery<br>- Team collaboration features<br>- Integration with 3rd-party tools<br>- Newsletter delivery | - Intuitive interface<br>- Reliable performance<br>- Extensive integrations | - Expensive paid plans<br>- Limited customization |
| **Inoreader** | Cloud | Cloud infrastructure, REST API | - Powerful search and filtering<br>- Custom RSS feed creation<br>- Social sharing<br>- Analytics dashboard | - Advanced search capabilities<br>- Flexible filtering<br>- Good free plan | - Less intuitive interface<br>- Limited personalization |
| **tt-rss** | Self-hosted | PHP backend, PostgreSQL/MySQL | - Open source, customizable<br>- Plugin system<br>- Feed aggregation and deduplication<br>- Email notifications | - Full control over data<br>- Extensive customization<br>- Free to use | - Requires self-hosting maintenance<br>- Less polished UI |

**Recommendation**: NewsBlur's architecture and features (especially deduplication and personalization) serve as a strong reference for `news-fetcher`. tt-rss provides insights into self-hosted implementation.

## 2. Deduplication Algorithms

| Algorithm | Approach | Accuracy | Performance | Strengths | Weaknesses | Use Case |
|-----------|----------|----------|-------------|-----------|------------|----------|
| **SimHash** (Google) | Fingerprinting using weighted hash collisions | High (95-98%) | Excellent (O(n)) | - Extremely fast comparison<br>- Compact fingerprint storage<br>- Robust to minor changes | - Less accurate for very short texts<br>- Requires careful weight tuning | Large-scale near-duplicate detection |
| **MinHash/LSH** | Jaccard similarity approximation | High (93-97%) | Good (O(n log n)) | - Effective for similar content<br>- Works well with shingling<br>- Scalable to large datasets | - Higher computational cost<br>- Requires parameter tuning | Medium-to-large scale deduplication |
| **TF-IDF + Cosine Similarity** | Vector space model with similarity scoring | High (94-98%) | Moderate (O(n^2)) | - Accurate for text similarity<br>- No training required<br>- Interpretable scores | - Slow for large datasets<br>- Sensitive to stopwords | Small-to-medium scale deduplication |
| **Shingling** | Character/n-gram overlap | Moderate (88-93%) | Moderate (O(n^2)) | - Simple to implement<br>- Language agnostic<br>- Robust to formatting changes | - High storage requirements<br>- Less accurate for semantic similarity | Basic deduplication tasks |

**Recommendation**: SimHash is recommended for `news-fetcher` due to its superior performance and accuracy at scale. For very short news snippets, a hybrid approach with TF-IDF could be used.

## 3. Clustering Algorithms

| Algorithm | Approach | Quality | Performance | Strengths | Weaknesses | Use Case |
|-----------|----------|---------|-------------|-----------|------------|----------|
| **HDBSCAN** (Hierarchical Density-Based) | Density-based clustering with hierarchical structure | Excellent | Good | - Handles varying cluster densities<br>- Automatically detects noise<br>- No need to specify cluster count | - Higher computational cost<br>- Parameter tuning required | Offline news article clustering |
| **Online Hierarchical Clustering** | Incremental cluster formation | Good | Excellent (O(n log n)) | - Real-time processing<br>- Handles streaming news<br>- Adaptive to concept drift | - Less accurate than offline methods<br>- Memory intensive | Streaming news clustering |
| **Hierarchical Agglomerative Clustering** | Bottom-up cluster merging | Good | Moderate (O(n^2)) | - Interpretable hierarchy<br>- No parameter tuning | Small-to-medium datasets<br>- Exploratory analysis |
| **K-Means** | Centroid-based | Moderate | Excellent | - Fast and simple<br>- Works well with vector data | - Requires cluster count specification<br>- Sensitive to initial centroids | Large datasets with uniform density clusters |

**Recommendation**: For initial implementation, use HDBSCAN for offline clustering and online hierarchical clustering for real-time news streams.

## 4. Ranking/Hotness Algorithms

| Algorithm | Approach | Key Factors | Strengths | Weaknesses | Use Case |
|-----------|----------|-------------|-----------|------------|----------|
| **Reddit Hotness** | Logarithmic time decay + net upvotes | Time decay, engagement (upvotes - downvotes) | - Balances recency and popularity<br>- Simple to implement<br>- Proven effectiveness | - Ignores source authority<br>- Sensitivity to vote manipulation | General news ranking |
| **Hacker News Hotness** | Polynomial time decay + upvotes | Time decay, upvotes | - Simple formula<br>- Focuses on quality (upvotes - 1)<br>- Open source | - Ignores source authority<br>- Decay rate may be too fast | Tech news ranking |
| **Exponential Time Decay** | Exponential decay with half-life parameter | Recency, engagement | - Adjustable decay rate<br>- Simple to implement<br>- Memory efficient | - Less effective than logarithmic decay | Time-sensitive content |
| **Source Authority Weighting** | PageRank-style domain authority scoring | Source reputation, content quality | - Improves credibility<br>- Reduces misinformation | - Requires training data<br>- Domain blocking possible | All news types |

**Recommendation**: Implement Reddit's hotness algorithm with additional source authority weighting (using domain reputation scores) for `news-fetcher`.

## 5. Diversity Selection Algorithms

| Algorithm | Approach | Quality | Performance | Strengths | Weaknesses | Use Case |
|-----------|----------|---------|-------------|-----------|------------|----------|
| **Maximal Marginal Relevance (MMR)** | Balances relevance and diversity | Excellent | Good | - Proven effectiveness<br>- Intuitive scoring<br>- Works with various features | - Requires similarity matrix<br>- Parameter tuning (λ) | News recommendation |
| **Submodular Function Maximization** | Greedy selection to maximize submodular function | Excellent | Moderate | - Theoretically optimal<br>- Handles complex constraints | - High computational cost<br>- Complex implementation | Content optimization |
| **Greedy Diversity Algorithms** | Select most dissimilar items iteratively | Good | Moderate | - Simple to implement<br>- Fast for small datasets | - Not theoretically optimal<br>- Sensitivity to initial items | Basic diversity selection |
| **Coverage-Based Selection** | Maximize feature coverage | Good | Good | - Ensures content variety<br>- Interpretable results | Topic coverage |

**Recommendation**: MMR is recommended for `news-fetcher` as it strikes a strong balance between relevance and diversity, and is straightforward to implement.

## 6. Summarization Approaches

| Approach | Type | Quality | Performance | Strengths | Weaknesses | Use Case |
|----------|------|---------|-------------|-----------|------------|----------|
| **Abridge-style Position-Aware Extractive** | Extractive | Excellent | Good | - Preserves article structure<br>- Maintains key information<br>- High readability | - Requires training data<br>- Language dependent | News article summarization |
| **TextRank** | Extractive (graph-based) | Good | Moderate | - No training required<br>- Language agnostic<br>- Good coherence | - Computationally expensive<br>- May miss key details | General text summarization |
| **Lead-3 (First 3 Sentences)** | Extractive | Good | Excellent | - Extremely fast<br>- Simple implementation<br>- High recall of key info | - Low precision<br>- May include irrelevant info | Quick summarization |
| **Centroid-Based** | Extractive (vector-based) | Good | Moderate | - Works well with clusters<br>- Scalable to large datasets | - Requires text vectorization<br>- Less readable | Clustered news summarization |

**Recommendation**: Abridge-style position-aware extractive summarization is recommended for high-quality news summaries. For fast summarization, use the Lead-3 approach as a fallback.

## Final Algorithm Recommendations for news-fetcher

| Component | Algorithm | Justification |
|-----------|-----------|---------------|
| **Deduplication** | SimHash | High accuracy, fast performance, and compact storage for large-scale deduplication |
| **Clustering** | HDBSCAN (offline) + Online Hierarchical Clustering (streaming) | Handles varying densities, detects noise, and provides real-time processing for streaming news |
| **Ranking** | Reddit Hotness + Source Authority Weighting | Balances recency and engagement, while improving credibility by weighting source reputation |
| **Diversity Selection** | Maximal Marginal Relevance (MMR) | Strikes optimal balance between relevance and diversity, ensuring users see important and varied content |
| **Summarization** | Abridge-style Position-Aware Extractive | Provides high-quality, readable summaries that maintain article coherence and key information |

## References

### Existing Tools
- NewsBlur: [https://newsblur.com/](https://newsblur.com/)
- Feedly: [https://feedly.com/](https://feedly.com/)
- Inoreader: [https://www.inoreader.com/](https://www.inoreader.com/)
- tt-rss: [https://tt-rss.org/](https://tt-rss.org/)

### Deduplication
- SimHash: [Google Research](https://research.google/pubs/pub33026/)
- MinHash/LSH: [Mining of Massive Datasets](http://www.mmds.org/)
- Shingling: [Text Deduplication Techniques](https://nlp.stanford.edu/IR-book/html/htmledition/near-duplicates-and-shingling-1.html)

### Clustering
- HDBSCAN: [https://hdbscan.readthedocs.io/](https://hdbscan.readthedocs.io/)
- Online Clustering: [Streaming Hierarchical Clustering](https://link.springer.com/chapter/10.1007/978-3-030-67661-2_16)

### Ranking
- Reddit Algorithm: [https://medium.com/hacking-and-gonzo/how-reddit-ranking-algorithms-work-ef111e33d0d9](https://medium.com/hacking-and-gonzo/how-reddit-ranking-algorithms-work-ef111e33d0d9)
- Hacker News Algorithm: [https://medium.com/hacking-and-gonzo/understanding-hacker-news-ranking-algorithm-1d9b0cf2c08d](https://medium.com/hacking-and-gonzo/understanding-hacker-news-ranking-algorithm-1d9b0cf2c08d)

### Diversity Selection
- MMR: [https://ieeexplore.ieee.org/document/94061](https://ieeexplore.ieee.org/document/94061)
- Submodular Functions: [https://theory.stanford.edu/~jvondrak/2019/05/22/submodular.pdf](https://theory.stanford.edu/~jvondrak/2019/05/22/submodular.pdf)

### Summarization
- Abridge: [https://abridge.io/](https://abridge.io/)
- TextRank: [https://web.eecs.umich.edu/~mihalcea/papers/mihalcea.emnlp04.pdf](https://web.eecs.umich.edu/~mihalcea/papers/mihalcea.emnlp04.pdf)

## Implementation Notes

### SimHash Implementation
- Use 64-bit or 128-bit hash for improved accuracy
- Tokenize text using word-level shingling (3-grams)
- Weight terms using TF-IDF scores
- Use Hamming distance ≤ 3 for duplicate detection

### HDBSCAN Implementation
- Use precomputed TF-IDF vectors as input
- Set `min_cluster_size` to 5-10 articles
- Use `min_samples` parameter to control noise detection

### Reddit Hotness Algorithm
- Implement formula: `score = log10(abs(net_upvotes)) + (time_since_submission / 45000)`
- Use net upvotes (upvotes - downvotes) with minimum value of 1
- Time decay parameter (45000 seconds ~12.5 hours) can be adjusted based on news cycle

### MMR Implementation
- Use BERT embeddings for semantic similarity
- Set λ (relevance/diversity tradeoff) to 0.6 (prioritizes relevance slightly)
- Limit diversity selection to top 10 articles per cluster

### Abridge-Style Summarization
- Focus on extracting key sentences from:
  - Title and subtitle
  - First paragraph (lead)
  - Important sections (quotations, statistics)
  - Last paragraph (conclusion)
