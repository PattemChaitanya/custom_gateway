"""Service discovery registry and healthy-instance routing selection."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


HEALTH_STATUS_TO_BOOL = {
    "healthy": True,
    "degraded": True,
    "unhealthy": False,
    "unknown": False,
}

SUPPORTED_ROUTING_STRATEGIES = {
    "round_robin", "weighted", "weighted_round_robin"}


@dataclass
class ServiceInstance:
    service: str
    instance_id: str
    url: str
    weight: int = 1
    healthy: bool = True
    health_status: str = "healthy"
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    ttl_seconds: int = 30

    @property
    def expired(self) -> bool:
        return (time.time() - self.last_heartbeat) > self.ttl_seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service": self.service,
            "instance_id": self.instance_id,
            "url": self.url,
            "weight": self.weight,
            "healthy": self.healthy,
            "health_status": self.health_status,
            "registered_at": self.registered_at,
            "last_heartbeat": self.last_heartbeat,
            "ttl_seconds": self.ttl_seconds,
            "expired": self.expired,
            "metadata": self.metadata,
        }


class ServiceRegistry:
    def __init__(self) -> None:
        self._services: Dict[str, Dict[str, ServiceInstance]] = {}
        self._rr_counters: Dict[str, int] = {}
        self._weighted_rr_state: Dict[str, Dict[str, float]] = {}

    def register_instance(
        self,
        service: str,
        instance_id: str,
        url: str,
        ttl_seconds: int = 30,
        weight: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ServiceInstance:
        if service not in self._services:
            self._services[service] = {}
            self._rr_counters[service] = 0

        instance = ServiceInstance(
            service=service,
            instance_id=instance_id,
            url=url,
            ttl_seconds=max(1, ttl_seconds),
            weight=max(1, weight),
            metadata=metadata or {},
            healthy=True,
            health_status="healthy",
        )
        self._services[service][instance_id] = instance
        return instance

    def heartbeat(
        self,
        service: str,
        instance_id: str,
        healthy: bool = True,
        health_status: Optional[str] = None,
    ) -> Optional[ServiceInstance]:
        instance = self._services.get(service, {}).get(instance_id)
        if not instance:
            return None
        instance.last_heartbeat = time.time()
        if health_status is not None:
            if health_status not in HEALTH_STATUS_TO_BOOL:
                raise ValueError(f"unsupported health status: {health_status}")
            instance.health_status = health_status
            instance.healthy = HEALTH_STATUS_TO_BOOL[health_status]
        else:
            instance.healthy = healthy
            instance.health_status = "healthy" if healthy else "unhealthy"
        return instance

    def mark_health(self, service: str, instance_id: str, healthy: bool) -> bool:
        instance = self._services.get(service, {}).get(instance_id)
        if not instance:
            return False
        instance.healthy = healthy
        instance.health_status = "healthy" if healthy else "unhealthy"
        return True

    def set_health_status(self, service: str, instance_id: str, health_status: str) -> bool:
        instance = self._services.get(service, {}).get(instance_id)
        if not instance:
            return False
        if health_status not in HEALTH_STATUS_TO_BOOL:
            raise ValueError(f"unsupported health status: {health_status}")
        instance.health_status = health_status
        instance.healthy = HEALTH_STATUS_TO_BOOL[health_status]
        return True

    def expire_instances(self) -> List[str]:
        expired: List[str] = []
        for service, instances in list(self._services.items()):
            for instance_id, instance in list(instances.items()):
                if instance.expired:
                    expired.append(f"{service}:{instance_id}")
                    del instances[instance_id]
            if not instances:
                del self._services[service]
                self._rr_counters.pop(service, None)
        return expired

    def list_instances(self, service: str, healthy_only: bool = False) -> List[ServiceInstance]:
        instances = list(self._services.get(service, {}).values())
        if healthy_only:
            instances = [i for i in instances if i.healthy and not i.expired]
        return instances

    def select_instance(self, service: str, strategy: str = "round_robin") -> Optional[ServiceInstance]:
        if strategy not in SUPPORTED_ROUTING_STRATEGIES:
            raise ValueError(f"unsupported routing strategy: {strategy}")

        candidates = self.list_instances(service, healthy_only=True)
        if not candidates:
            return None

        if strategy == "weighted":
            total = sum(max(1, i.weight) for i in candidates)
            pick = random.uniform(0, total)
            running = 0.0
            for instance in candidates:
                running += max(1, instance.weight)
                if pick <= running:
                    return instance
            return candidates[-1]

        if strategy == "weighted_round_robin":
            state = self._weighted_rr_state.setdefault(service, {})
            total_weight = sum(max(1, i.weight) for i in candidates)
            for instance in candidates:
                state.setdefault(instance.instance_id, 0.0)
                state[instance.instance_id] += max(1, instance.weight)

            selected = max(
                candidates, key=lambda i: state.get(i.instance_id, 0.0))
            state[selected.instance_id] = state.get(
                selected.instance_id, 0.0) - total_weight

            # Prune state keys for instances no longer present.
            present_ids = {i.instance_id for i in candidates}
            for stale_id in list(state.keys()):
                if stale_id not in present_ids:
                    state.pop(stale_id, None)

            return selected

        idx = self._rr_counters.get(service, 0) % len(candidates)
        self._rr_counters[service] = (idx + 1) % len(candidates)
        return candidates[idx]
