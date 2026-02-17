"""Synchronous strategy implementations used by tests.

These provide simple in-memory strategies with the synchronous API the
tests expect (`is_allowed(key)` returning True/False or similar).
"""
import time
from collections import defaultdict, deque


class FixedWindowStrategy:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.counters = defaultdict(lambda: [0, time.time()])

    def is_allowed(self, key: str) -> bool:
        count, start = self.counters[key]
        now = time.time()
        if now - start >= self.window_seconds:
            self.counters[key] = [1, now]
            return True
        if count < self.max_requests:
            self.counters[key][0] += 1
            return True
        return False


class SlidingWindowStrategy:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.logs = defaultdict(deque)

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        q = self.logs[key]
        while q and now - q[0] > self.window_seconds:
            q.popleft()
        if len(q) < self.max_requests:
            q.append(now)
            return True
        return False


class TokenBucketStrategy:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.state = {}  # key -> (tokens, last_ts)

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        tokens, last = self.state.get(key, (self.capacity, now))
        # refill
        tokens = min(self.capacity, tokens + (now - last) * self.refill_rate)
        if tokens >= 1:
            tokens -= 1
            self.state[key] = (tokens, now)
            return True
        self.state[key] = (tokens, now)
        return False
