#!/usr/bin/env python3
"""Test script for output module."""

import sys
sys.path.append('/home/miniade/repos/news-fetcher/src')

from news_fetcher.output import OutputFormatter
from news_fetcher.models import Article
from datetime import datetime

# Create test articles
test_articles = [
    Article(
        id="1",
        title="Google announces BERT search algorithm update",
        content="Google has announced a major update to its search algorithm. The new update, called BERT, is designed to better understand natural language queries. According to Google, BERT will affect 10% of all search queries.",
        url="https://example.com/google-bert-update",
        source="TechCrunch",
        published_at=datetime.now()
    ),
    Article(
        id="2",
        title="Microsoft launches new Azure AI services",
        content="Microsoft has unveiled a suite of new AI services for its Azure cloud platform. The services include advanced machine learning capabilities and natural language processing tools.",
        url="https://example.com/microsoft-azure-ai",
        source="ZDNet",
        published_at=datetime.now()
    )
]

# Test 1: JSON format
print("=== Test 1: JSON Format ===")
formatter = OutputFormatter(format="json")
json_output = formatter.format(test_articles)
print(json_output)
print()

# Test 2: Markdown format
print("=== Test 2: Markdown Format ===")
formatter = OutputFormatter(format="markdown")
md_output = formatter.format(test_articles)
print(md_output)
print()

# Test 3: CSV format
print("=== Test 3: CSV Format ===")
formatter = OutputFormatter(format="csv")
csv_output = formatter.format(test_articles)
print(csv_output)
