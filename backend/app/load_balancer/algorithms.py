"""Load balancing algorithms."""

import random
from typing import List, Dict, Any, Optional
from collections import defaultdict
from app.logging_config import get_logger

logger = get_logger("load_balancer")


class Backend:
    """Represents a backend server."""
    
    def __init__(self, url: str, weight: int = 1, healthy: bool = True):
        self.url = url
        self.weight = weight
        self.healthy = healthy
        self.active_connections = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "weight": self.weight,
            "healthy": self.healthy,
            "active_connections": self.active_connections,
        }


class RoundRobinLoadBalancer:
    """Round-robin load balancing algorithm."""
    
    def __init__(self, backends: List[Dict[str, Any]]):
        self.backends = [Backend(b["url"], b.get("weight", 1)) for b in backends]
        self.current_index = 0
    
    def select_backend(self) -> Optional[Backend]:
        """Select next backend using round-robin."""
        if not self.backends:
            return None
        
        # Filter healthy backends
        healthy_backends = [b for b in self.backends if b.healthy]
        
        if not healthy_backends:
            logger.warning("No healthy backends available")
            return None
        
        # Round-robin selection
        backend = healthy_backends[self.current_index % len(healthy_backends)]
        self.current_index = (self.current_index + 1) % len(healthy_backends)
        
        return backend
    
    def mark_backend_healthy(self, url: str, healthy: bool = True):
        """Mark a backend as healthy or unhealthy."""
        for backend in self.backends:
            if backend.url == url:
                backend.healthy = healthy
                logger.info(f"Backend {url} marked as {'healthy' if healthy else 'unhealthy'}")
                break


class LeastConnectionsLoadBalancer:
    """Least connections load balancing algorithm."""
    
    def __init__(self, backends: List[Dict[str, Any]]):
        self.backends = [Backend(b["url"], b.get("weight", 1)) for b in backends]
    
    def select_backend(self) -> Optional[Backend]:
        """Select backend with least active connections."""
        healthy_backends = [b for b in self.backends if b.healthy]
        
        if not healthy_backends:
            logger.warning("No healthy backends available")
            return None
        
        # Find backend with minimum connections
        backend = min(healthy_backends, key=lambda b: b.active_connections)
        backend.active_connections += 1
        
        return backend
    
    def release_connection(self, url: str):
        """Release a connection from a backend."""
        for backend in self.backends:
            if backend.url == url:
                backend.active_connections = max(0, backend.active_connections - 1)
                break
    
    def mark_backend_healthy(self, url: str, healthy: bool = True):
        """Mark a backend as healthy or unhealthy."""
        for backend in self.backends:
            if backend.url == url:
                backend.healthy = healthy
                logger.info(f"Backend {url} marked as {'healthy' if healthy else 'unhealthy'}")
                break


class WeightedLoadBalancer:
    """Weighted load balancing algorithm."""
    
    def __init__(self, backends: List[Dict[str, Any]]):
        self.backends = [Backend(b["url"], b.get("weight", 1)) for b in backends]
    
    def select_backend(self) -> Optional[Backend]:
        """Select backend based on weights."""
        healthy_backends = [b for b in self.backends if b.healthy]
        
        if not healthy_backends:
            logger.warning("No healthy backends available")
            return None
        
        # Calculate total weight
        total_weight = sum(b.weight for b in healthy_backends)
        
        if total_weight == 0:
            return random.choice(healthy_backends)
        
        # Weighted random selection
        rand = random.uniform(0, total_weight)
        cumulative = 0
        
        for backend in healthy_backends:
            cumulative += backend.weight
            if rand <= cumulative:
                return backend
        
        return healthy_backends[-1]
    
    def mark_backend_healthy(self, url: str, healthy: bool = True):
        """Mark a backend as healthy or unhealthy."""
        for backend in self.backends:
            if backend.url == url:
                backend.healthy = healthy
                logger.info(f"Backend {url} marked as {'healthy' if healthy else 'unhealthy'}")
                break


def create_load_balancer(algorithm: str, backends: List[Dict[str, Any]]):
    """Factory function to create appropriate load balancer."""
    if algorithm == "least_connections":
        return LeastConnectionsLoadBalancer(backends)
    elif algorithm == "weighted":
        return WeightedLoadBalancer(backends)
    else:
        return RoundRobinLoadBalancer(backends)
