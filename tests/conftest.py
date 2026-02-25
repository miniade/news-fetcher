"""
Test configuration and shared fixtures for the news-fetcher project.
"""

import pytest
import responses
from datetime import datetime
from typing import Dict, List, Any
from unittest.mock import MagicMock


@pytest.fixture
def sample_rss_feed():
    """Sample RSS feed XML for testing feed parsing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Test News Feed</title>
        <link>https://example.com/news</link>
        <description>Sample news feed for testing</description>
        <pubDate>Sat, 25 Feb 2025 12:00:00 GMT</pubDate>
        <item>
            <title>Tech Giants Announce New AI Partnership</title>
            <link>https://example.com/news/ai-partnership</link>
            <description>Leading technology companies join forces to advance artificial intelligence research</description>
            <pubDate>Sat, 25 Feb 2025 10:30:00 GMT</pubDate>
            <guid>https://example.com/news/ai-partnership</guid>
        </item>
        <item>
            <title>Global Markets Hit Record Highs</title>
            <link>https://example.com/news/market-highs</link>
            <description>Stock markets around the world reach new all-time highs amid economic recovery</description>
            <pubDate>Sat, 25 Feb 2025 09:15:00 GMT</pubDate>
            <guid>https://example.com/news/market-highs</guid>
        </item>
        <item>
            <title>Climate Summit Reaches Historic Agreement</title>
            <link>https://example.com/news/climate-agreement</link>
            <description>World leaders commit to ambitious carbon reduction targets</description>
            <pubDate>Sat, 25 Feb 2025 08:00:00 GMT</pubDate>
            <guid>https://example.com/news/climate-agreement</guid>
        </item>
    </channel>
</rss>
"""


@pytest.fixture
def sample_html_news_page():
    """Sample HTML content for a news article page."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Tech Giants Announce New AI Partnership - Example News</title>
    <meta charset="UTF-8">
</head>
<body>
    <article>
        <h1>Tech Giants Announce New AI Partnership</h1>
        <div class="byline">By John Doe | Feb 25, 2025</div>
        <div class="content">
            <p>Leading technology companies have announced a groundbreaking partnership to advance artificial intelligence research.</p>
            <p>The collaboration brings together experts from multiple industries to develop innovative AI solutions.</p>
            <h2>Key Areas of Focus</h2>
            <ul>
                <li>Machine learning algorithms</li>
                <li>Natural language processing</li>
                <li>Computer vision applications</li>
            </ul>
            <p>This partnership is expected to accelerate AI development and bring new technologies to market faster.</p>
        </div>
    </article>
</body>
</html>
"""


@pytest.fixture
def mock_http_responses():
    """Fixture to set up mock HTTP responses using responses library."""
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def config_fixture():
    """Sample configuration for testing different scenarios."""
    return {
        "feeds": [
            "https://example.com/feed1.rss",
            "https://example.com/feed2.rss"
        ],
        "fetch": {
            "timeout": 10,
            "retries": 3
        },
        "normalize": {
            "min_length": 50,
            "max_length": 5000
        },
        "dedup": {
            "threshold": 0.85
        },
        "cluster": {
            "threshold": 0.7
        },
        "rank": {
            "algorithm": "tfidf"
        },
        "diversify": {
            "max_per_topic": 3
        },
        "summarize": {
            "model": "default"
        },
        "output": {
            "formats": ["json", "rss"],
            "directory": "output"
        }
    }


@pytest.fixture
def sample_news_items():
    """Sample normalized news items for testing processing stages."""
    return [
        {
            "id": "1",
            "title": "Tech Giants Announce New AI Partnership",
            "content": "Leading technology companies have announced a groundbreaking partnership to advance artificial intelligence research. The collaboration brings together experts from multiple industries to develop innovative AI solutions. Key areas of focus include machine learning algorithms, natural language processing, and computer vision applications.",
            "url": "https://example.com/news/ai-partnership",
            "source": "Example News",
            "published_at": datetime(2025, 2, 25, 10, 30),
            "author": "John Doe",
            "language": "en",
            "keywords": ["ai", "partnership", "technology"]
        },
        {
            "id": "2",
            "title": "Global Markets Hit Record Highs",
            "content": "Stock markets around the world reach new all-time highs amid economic recovery. Investors are optimistic about the future of global economies.",
            "url": "https://example.com/news/market-highs",
            "source": "Financial Times",
            "published_at": datetime(2025, 2, 25, 9, 15),
            "author": "Jane Smith",
            "language": "en",
            "keywords": ["markets", "economy", "finance"]
        },
        {
            "id": "3",
            "title": "Climate Summit Reaches Historic Agreement",
            "content": "World leaders commit to ambitious carbon reduction targets. The agreement aims to limit global warming to 1.5 degrees Celsius.",
            "url": "https://example.com/news/climate-agreement",
            "source": "Environmental News",
            "published_at": datetime(2025, 2, 25, 8, 0),
            "author": "Michael Green",
            "language": "en",
            "keywords": ["climate", "environment", "agreement"]
        }
    ]


@pytest.fixture
def mock_file_system():
    """Fixture to mock file system operations."""
    mock = MagicMock()
    mock.open = MagicMock()
    mock.exists = MagicMock(return_value=True)
    mock.isdir = MagicMock(return_value=True)
    mock.mkdir = MagicMock()
    return mock