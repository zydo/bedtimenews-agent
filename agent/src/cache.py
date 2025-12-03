"""Caching utilities for query results and embeddings."""

import hashlib
from typing import Dict, Optional, Tuple


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
    Simple LRU (Least Recently Used) cache implementation.

    Evicts least recently used items when capacity is reached.
    """

    def __init__(self, capacity: int = 1000):
        """
        Initialize the cache.

        Args:
            capacity: Maximum number of items to store
        """
        self.capacity = capacity
        self.cache: Dict[str, Tuple[object, int]] = {}  # key -> (value, access_count)
        self._access_counter = 0

    def get(self, key: str) -> Optional[object]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found, None otherwise
        """
        if key in self.cache:
            # Update access count for LRU
            value, _ = self.cache[key]
            self._access_counter += 1
            self.cache[key] = (value, self._access_counter)
            return value
        return None

    def put(self, key: str, value: object) -> None:
        """
        Put value into cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        self._access_counter += 1

        if key in self.cache:
            # Update existing entry
            self.cache[key] = (value, self._access_counter)
        else:
            # Add new entry, evict if at capacity
            if len(self.cache) >= self.capacity:
                self._evict_lru()
            self.cache[key] = (value, self._access_counter)

    def _evict_lru(self) -> None:
        """Evict the least recently used item from cache."""
        if not self.cache:
            return

        # Find item with lowest access count
        lru_key = min(self.cache, key=lambda k: self.cache[k][1])
        del self.cache[lru_key]

    def clear(self) -> None:
        """Clear all cached items."""
        self.cache.clear()
        self._access_counter = 0

    def size(self) -> int:
        """Return current cache size."""
        return len(self.cache)
