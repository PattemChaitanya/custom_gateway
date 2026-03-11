"""Autoscaling simulation loop driven by queue depth and latency signals."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict


@dataclass
class AutoscalerSignal:
    queue_depth: int
    latency_p95_ms: float


class AutoscalerLoop:
    def __init__(
        self,
        min_replicas: int = 1,
        max_replicas: int = 10,
        scale_up_queue_depth: int = 25,
        scale_down_queue_depth: int = 5,
        scale_up_latency_ms: float = 400,
        scale_down_latency_ms: float = 120,
        cooldown_seconds: int = 30,
    ) -> None:
        self.min_replicas = max(1, min_replicas)
        self.max_replicas = max(self.min_replicas, max_replicas)
        self.scale_up_queue_depth = max(1, scale_up_queue_depth)
        self.scale_down_queue_depth = max(
            0, min(scale_down_queue_depth, self.scale_up_queue_depth - 1))
        self.scale_up_latency_ms = max(1.0, scale_up_latency_ms)
        self.scale_down_latency_ms = max(
            1.0, min(scale_down_latency_ms, self.scale_up_latency_ms - 1))
        self.cooldown_seconds = max(0, cooldown_seconds)
        self.current_replicas = self.min_replicas
        self.last_scaled_at = 0.0

    def evaluate(self, signal: AutoscalerSignal, now: float | None = None) -> Dict[str, int | str | float]:
        ts = now if now is not None else time.time()
        in_cooldown = (ts - self.last_scaled_at) < self.cooldown_seconds
        reason = "steady"

        if in_cooldown:
            return {
                "replicas": self.current_replicas,
                "action": "none",
                "reason": "cooldown",
            }

        should_scale_up = (
            signal.queue_depth >= self.scale_up_queue_depth
            or signal.latency_p95_ms >= self.scale_up_latency_ms
        )
        should_scale_down = (
            signal.queue_depth <= self.scale_down_queue_depth
            and signal.latency_p95_ms <= self.scale_down_latency_ms
        )

        if should_scale_up and self.current_replicas < self.max_replicas:
            self.current_replicas += 1
            self.last_scaled_at = ts
            reason = "queue_or_latency_high"
            return {"replicas": self.current_replicas, "action": "scale_up", "reason": reason}

        if should_scale_down and self.current_replicas > self.min_replicas:
            self.current_replicas -= 1
            self.last_scaled_at = ts
            reason = "queue_and_latency_low"
            return {"replicas": self.current_replicas, "action": "scale_down", "reason": reason}

        return {"replicas": self.current_replicas, "action": "none", "reason": reason}
