"""Compatibility package mirroring app.load_balancer.

Re-exports algorithms and manager classes expected by existing tests.
"""
from app.load_balancer import algorithms as algorithms
from app.load_balancer.pool import BackendPoolManager

# Provide names expected by older imports
from types import SimpleNamespace


class LoadBalancerManager(BackendPoolManager):
    pass


__all__ = [
    "algorithms",
    "LoadBalancerManager",
]
