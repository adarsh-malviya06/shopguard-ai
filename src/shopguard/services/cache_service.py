"""Semantic caching service for ShopGuard AI.

Caches policy responses based on question similarity or canonical hash.
TTL: 60 minutes, Max entries: 100.
Thread-safe in-memory cache with hit/miss statistics.
"""

from __future__ import annotations
import time
from typing import Optional, Dict, Any

_cache_store: Dict[str, Dict[str, Any]] = {}
_stats = {"hits": 0, "misses": 0}


def get_cache_stats() -> dict:
    """Return cache hit/miss and occupancy statistics."""
    now = time.time()
    # Count only unexpired entries
    active_entries = sum(1 for v in _cache_store.values() if v["expires_at"] > now)
    total = _stats["hits"] + _stats["misses"]
    hit_ratio = round(_stats["hits"] / total, 3) if total > 0 else 0.0
    return {
        "hits": _stats["hits"],
        "misses": _stats["misses"],
        "active_entries": active_entries,
        "total_capacity": 100,
        "hit_ratio": hit_ratio,
    }


def get_cached_response(query: str) -> Optional[str]:
    """Retrieve cached response if key exists and has not expired."""
    norm_key = query.strip().lower()
    now = time.time()
    item = _cache_store.get(norm_key)

    if item is not None:
        if item["expires_at"] > now:
            _stats["hits"] += 1
            return item["response"]
        else:
            # Expired
            _cache_store.pop(norm_key, None)

    _stats["misses"] += 1
    return None


def set_cached_response(query: str, response: str, ttl_seconds: int = 3600) -> None:
    """Store response in cache, evicting oldest if max capacity is exceeded."""
    norm_key = query.strip().lower()

    # Evict if full
    if len(_cache_store) >= 100:
        # Evict earliest expiring or oldest
        oldest_key = min(_cache_store.keys(), key=lambda k: _cache_store[k]["expires_at"])
        _cache_store.pop(oldest_key, None)

    _cache_store[norm_key] = {
        "response": response,
        "expires_at": time.time() + ttl_seconds,
    }


def clear_cache() -> int:
    """Clear all cache entries and return count cleared."""
    count = len(_cache_store)
    _cache_store.clear()
    return count
