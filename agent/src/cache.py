"""Caching utilities for query results and embeddings."""

import hashlib
import sys
from collections import OrderedDict
from typing import Any, Optional


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


def _estimate_size(obj: Any) -> int:
    """Estimate memory footprint of a cached object in bytes."""
    return sys.getsizeof(obj)


class LRUCache:
    """
    LRU (Least Recently Used) cache using OrderedDict for O(1) eviction.

    Tracks both item count and memory footprint. Evicts when either
    capacity or max_memory is exceeded.
    """

    def __init__(self, capacity: int = 1000, max_memory_mb: float = 100):
        """
        Initialize the cache.

        Args:
            capacity: Maximum number of items to store
            max_memory_mb: Maximum memory usage in megabytes (approximate)
        """
        self.capacity = capacity
        self.max_memory = int(max_memory_mb * 1024 * 1024)
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self._sizes: OrderedDict[str, int] = OrderedDict()
        self._total_size = 0

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
            self._sizes.move_to_end(key)
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
            self._total_size -= self._sizes[key]
            size = _estimate_size(value)
            self.cache[key] = value
            self._sizes[key] = size
            self._total_size += size
            self.cache.move_to_end(key)
            self._sizes.move_to_end(key)
        else:
            size = _estimate_size(value)
            while (len(self.cache) >= self.capacity or
                   (self._total_size + size > self.max_memory and self.cache)):
                self._evict_one()
            self.cache[key] = value
            self._sizes[key] = size
            self._total_size += size

    def _evict_one(self) -> None:
        """Evict the least recently used item."""
        _, size = self._sizes.popitem(last=False)
        self.cache.popitem(last=False)
        self._total_size -= size

    def clear(self) -> None:
        """Clear all cached items."""
        self.cache.clear()
        self._sizes.clear()
        self._total_size = 0

    def size(self) -> int:
        """Return current cache size."""
        return len(self.cache)

    def memory_usage_mb(self) -> float:
        """Return approximate memory usage in megabytes."""
        return self._total_size / (1024 * 1024)
