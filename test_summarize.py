#!/usr/bin/env python3
"""Test script for summarize module."""

import sys
sys.path.append('/home/miniade/repos/news-fetcher/src')

from news_fetcher.summarize import ArticleSummarizer

# Test data
sample_text = """
Google has announced a major update to its search algorithm. The new update,
called BERT, is designed to better understand natural language queries.
According to Google, BERT will affect 10% of all search queries. "This is a
significant improvement," said John Mueller, Google's Search Advocate.
The update will roll out to all languages over the next few weeks.
""".strip()

# Test 1: Position-based summarization
print("=== Test 1: Position-based Summarization ===")
summarizer = ArticleSummarizer(method="position", max_sentences=3)
summary = summarizer.summarize_text(sample_text, "Google Search Algorithm Update")
print(summary)
print()

# Test 2: Lead-N summarization
print("=== Test 2: Lead-N Summarization ===")
summarizer = ArticleSummarizer(method="lead", max_sentences=2)
summary = summarizer.summarize_text(sample_text)
print(summary)
print()

# Test 3: Extract key sentences
print("=== Test 3: Extract Key Sentences ===")
summarizer = ArticleSummarizer()
key_sentences = summarizer.extract_key_sentences(sample_text, n=2)
for i, sent in enumerate(key_sentences, 1):
    print(f"{i}. {sent}")
