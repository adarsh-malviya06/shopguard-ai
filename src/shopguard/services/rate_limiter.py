"""In-memory rate limiter for ShopGuard API."""

import time
from collections import defaultdict
from typing import Dict, List

# session_id -> list of request timestamps
_session_requests: Dict[str, List[float]] = defaultdict(list)
_global_requests: List[float] = []

GLOBAL_LIMIT_PER_MIN = 60
SESSION_LIMIT_PER_MIN = 20


def is_rate_limited(session_id: str = "default") -> tuple[bool, int]:
    """Check if session or global rate limits are exceeded.

    Returns (is_limited, retry_after_seconds).
    """
    now = time.time()
    cutoff = now - 60.0

    # Prune global
    global _global_requests
    _global_requests = [t for t in _global_requests if t > cutoff]
    if len(_global_requests) >= GLOBAL_LIMIT_PER_MIN:
        earliest = _global_requests[0]
        return True, int(60 - (now - earliest)) + 1

    # Prune session
    session_history = [t for t in _session_requests[session_id] if t > cutoff]
    _session_requests[session_id] = session_history
    if len(session_history) >= SESSION_LIMIT_PER_MIN:
        earliest = session_history[0]
        return True, int(60 - (now - earliest)) + 1

    # Record hit
    _global_requests.append(now)
    _session_requests[session_id].append(now)
    return False, 0
