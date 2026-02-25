"""
Custom exceptions for news-fetcher application.

This module defines all custom exception classes used throughout the
news-fetcher application to handle various error conditions.
"""


class NewsFetcherError(Exception):
    """Base exception class for all news-fetcher errors."""

    def __init__(self, message: str = "An error occurred in news-fetcher"):
        """Initialize the exception.

        Args:
            message: Error message describing the exception.
        """
        self.message = message
        super().__init__(self.message)


class FetchError(NewsFetcherError):
    """Exception raised when fetching news articles fails."""

    def __init__(self, url: str, message: str = "Failed to fetch news"):
        """Initialize the exception.

        Args:
            url: URL that failed to fetch.
            message: Error message describing the exception.
        """
        self.url = url
        self.message = f"{message}: {url}"
        super().__init__(self.message)


class ParseError(NewsFetcherError):
    """Exception raised when parsing news articles fails."""

    def __init__(self, source: str, message: str = "Failed to parse news"):
        """Initialize the exception.

        Args:
            source: Source that failed to parse.
            message: Error message describing the exception.
        """
        self.source = source
        self.message = f"{message}: {source}"
        super().__init__(self.message)


class ConfigError(NewsFetcherError):
    """Exception raised when configuration errors occur."""

    def __init__(self, message: str = "Configuration error"):
        """Initialize the exception.

        Args:
            message: Error message describing the exception.
        """
        self.message = message
        super().__init__(self.message)


class ProcessingError(NewsFetcherError):
    """Exception raised when processing news articles fails."""

    def __init__(self, message: str = "Failed to process news"):
        """Initialize the exception.

        Args:
            message: Error message describing the exception.
        """
        self.message = message
        super().__init__(self.message)


class SourceError(NewsFetcherError):
    """Exception raised when source-related errors occur."""

    def __init__(self, source: str, message: str = "Source error"):
        """Initialize the exception.

        Args:
            source: Source that caused the error.
            message: Error message describing the exception.
        """
        self.source = source
        self.message = f"{message}: {source}"
        super().__init__(self.message)
