"""Compatibility wrapper for load balancing algorithms.

Re-exports algorithm implementations from `app.load_balancer.algorithms`.
"""
from app.load_balancer.algorithms import (
    RoundRobinLoadBalancer,
    LeastConnectionsLoadBalancer,
    WeightedLoadBalancer,
)

# Provide the class names expected by existing tests


class RoundRobinAlgorithm:
    def __init__(self, backends):
        self._impl = RoundRobinLoadBalancer(backends)

    def select_backend(self):
        b = self._impl.select_backend()
        if not b:
            return None
        # Normalize to the simple dict shape tests expect
        return {"url": b.url, "healthy": b.healthy}

    def mark_backend_healthy(self, url: str, healthy: bool = True):
        return self._impl.mark_backend_healthy(url, healthy)


class LeastConnectionsAlgorithm:
    def __init__(self, backends):
        self._impl = LeastConnectionsLoadBalancer(backends)

    def select_backend(self):
        b = self._impl.select_backend()
        if not b:
            return None
        return {"url": b.url, "healthy": b.healthy}

    def release_connection(self, url: str):
        return self._impl.release_connection(url)

    def mark_backend_healthy(self, url: str, healthy: bool = True):
        return self._impl.mark_backend_healthy(url, healthy)


class WeightedRoundRobinAlgorithm:
    def __init__(self, backends):
        self._impl = WeightedLoadBalancer(backends)

    def select_backend(self):
        b = self._impl.select_backend()
        if not b:
            return None
        return {"url": b.url, "healthy": b.healthy, "weight": b.weight}

    def mark_backend_healthy(self, url: str, healthy: bool = True):
        return self._impl.mark_backend_healthy(url, healthy)


__all__ = [
    "RoundRobinAlgorithm",
    "LeastConnectionsAlgorithm",
    "WeightedRoundRobinAlgorithm",
]
