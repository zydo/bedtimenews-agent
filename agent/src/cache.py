"""Caching utilities for query results and embeddings."""

import hashlib
from collections import OrderedDict
from typing import Any, Dict, Optional


def hash_query(query: str, match_threshold: float, match_count: int) -> str:
    """
    Generate cache key for query parameters.

    Args:
        query: Search query string
        match_threshold: Similarity threshold
        match_count: Maximum results count

    Returns:
        MD5 hash of the query parameters
    """
    key_str = f"{query}:{match_threshold}:{match_count}"
    return hashlib.md5(key_str.encode()).hexdigest()


class LRUCache:
    """
    LRU (Least Recently Used) cache using OrderedDict for O(1) eviction.

    OrderedDict.move_to_end() and popitem(last=False) provide constant-time
    access updates and eviction respectively.
    """

    def __init__(self, capacity: int = 1000):
        """
        Initialize the cache.

        Args:
            capacity: Maximum number of items to store
        """
        self.capacity = capacity
        self.cache: OrderedDict[str, Any] = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found, None otherwise
        """
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def put(self, key: str, value: Any) -> None:
        """
        Put value into cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        if key in self.cache:
            self.cache.move_to_end(key)
            self.cache[key] = value
        else:
            if len(self.cache) >= self.capacity:
                self.cache.popitem(last=False)
            self.cache[key] = value

    def clear(self) -> None:
        """Clear all cached items."""
        self.cache.clear()

    def size(self) -> int:
        """Return current cache size."""
        return len(self.cache)
