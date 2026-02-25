#!/usr/bin/env python3
"""Test script to verify the dedup and cluster modules implementation."""

import sys
from datetime import datetime

# Add src directory to path
sys.path.insert(0, '/home/miniade/repos/news-fetcher/src')

from news_fetcher.dedup import SimHash, Deduplicator, compute_shingles, jaccard_similarity
from news_fetcher.cluster import ArticleClusterer, ClusterManager
from news_fetcher.models import Article, Cluster

# Test 1: Deduplication
print("=== Testing Deduplication ===")
try:
    # Test SimHash
    simhash = SimHash(hashbits=64)
    text1 = "Tech Giants Announce New AI Partnership"
    text2 = "New AI Partnership Announced by Tech Giants"
    text3 = "Climate Change Impacts on Agriculture"
    
    hash1 = simhash.compute(text1)
    hash2 = simhash.compute(text2)
    hash3 = simhash.compute(text3)
    
    distance12 = simhash.distance(hash1, hash2)
    distance13 = simhash.distance(hash1, hash3)
    
    print(f"Text1 hash: {hash1}")
    print(f"Text2 hash: {hash2}")
    print(f"Text3 hash: {hash3}")
    print(f"Distance 1-2: {distance12} (should be small)")
    print(f"Distance 1-3: {distance13} (should be large)")
    
    # Test Deduplicator
    deduplicator = Deduplicator(threshold=10)  # Lower threshold for test
    
    # Add documents
    dupe_id = deduplicator.add_document("doc1", text1)
    print(f"Added doc1, duplicate: {dupe_id}")
    
    dupe_id = deduplicator.add_document("doc2", text2)
    print(f"Added doc2, duplicate: {dupe_id}")
    
    dupe_id = deduplicator.add_document("doc3", text3)
    print(f"Added doc3, duplicate: {dupe_id}")
    
    print()
    
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    print(traceback.format_exc())

# Test 2: Clustering
print("=== Testing Clustering ===")
try:
    # Create test articles
    articles = [
        Article(
            id="1",
            title="Tech Giants Announce New AI Partnership",
            content="Leading tech companies announce AI partnership",
            url="https://example.com/news1",
            source="Source1",
            published_at=datetime(2025, 2, 25)
        ),
        Article(
            id="2",
            title="New AI Partnership Announced by Tech Giants",
            content="Tech companies announce new AI partnership",
            url="https://example.com/news2",
            source="Source2",
            published_at=datetime(2025, 2, 25)
        ),
        Article(
            id="3",
            title="Climate Change Impacts on Agriculture",
            content="Climate change effects on global agriculture",
            url="https://example.com/news3",
            source="Source3",
            published_at=datetime(2025, 2, 25)
        ),
        Article(
            id="4",
            title="AI Revolution in Healthcare",
            content="Artificial intelligence transforming healthcare industry",
            url="https://example.com/news4",
            source="Source4",
            published_at=datetime(2025, 2, 25)
        ),
        Article(
            id="5",
            title="Machine Learning in Medical Diagnosis",
            content="Machine learning applications in medical diagnosis",
            url="https://example.com/news5",
            source="Source5",
            published_at=datetime(2025, 2, 25)
        ),
        # Add more similar articles
        Article(
            id="6",
            title="AI Partnership Announced by Tech Leaders",
            content="Leading technology companies announce artificial intelligence collaboration",
            url="https://example.com/news6",
            source="Source6",
            published_at=datetime(2025, 2, 25)
        ),
        Article(
            id="7",
            title="Climate Change Effects on Farming",
            content="Global warming impacts on agricultural production",
            url="https://example.com/news7",
            source="Source7",
            published_at=datetime(2025, 2, 25)
        ),
        Article(
            id="8",
            title="Deep Learning in Healthcare",
            content="Deep learning technologies improving medical diagnosis",
            url="https://example.com/news8",
            source="Source8",
            published_at=datetime(2025, 2, 25)
        )
    ]
    
    # Test clustering
    clusterer = ArticleClusterer(min_cluster_size=2, min_samples=1)
    clusters = clusterer.fit(articles)
    
    print(f"Found {len(clusters)} clusters")
    
    for i, cluster in enumerate(clusters):
        print(f"\nCluster {i+1} (ID: {cluster.id}):")
        print(f"  Articles: {[article.id for article in cluster.articles]}")
        print(f"  Representative: {cluster.representative_article.title}")
        print(f"  Centroid dimension: {len(cluster.centroid) if cluster.centroid else 0}")
    
    print()
    
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    print(traceback.format_exc())

# Test 3: Cluster Manager
print("=== Testing Cluster Manager ===")
try:
    manager = ClusterManager()
    
    # Create some clusters
    cluster1 = Cluster(
        id="cluster1",
        articles=[articles[0], articles[1]]
    )
    
    cluster2 = Cluster(
        id="cluster2",
        articles=[articles[2]]
    )
    
    cluster3 = Cluster(
        id="cluster3",
        articles=[articles[3], articles[4]]
    )
    
    manager.add_cluster(cluster1)
    manager.add_cluster(cluster2)
    manager.add_cluster(cluster3)
    
    print(f"Initial clusters: {len(manager.get_all_clusters())}")
    
    # Test merge
    merged_cluster = manager.merge_clusters("cluster1", "cluster3")
    print(f"After merge: {len(manager.get_all_clusters())} clusters")
    print(f"Merged cluster has {len(merged_cluster.articles)} articles")
    
    print()
    
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    print(traceback.format_exc())

print("=== All tests completed ===")
