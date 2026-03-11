"""Simple queue + worker lease scheduler for control-loop jobs."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class JobPayload:
    job_type: str
    payload: Dict[str, Any]
    max_retries: int = 3


@dataclass
class Job:
    id: str
    data: JobPayload
    created_at: float = field(default_factory=time.time)
    available_at: float = field(default_factory=time.time)
    attempts: int = 0
    lease_owner: Optional[str] = None
    lease_expires_at: Optional[float] = None


@dataclass
class LeasedJob:
    id: str
    job_type: str
    payload: Dict[str, Any]
    attempts: int
    lease_owner: str
    lease_expires_at: float


class ControlLoopScheduler:
    def __init__(self, lease_seconds: int = 30, base_backoff_seconds: int = 2, max_backoff_seconds: int = 60) -> None:
        self.lease_seconds = max(1, lease_seconds)
        self.base_backoff_seconds = max(1, base_backoff_seconds)
        self.max_backoff_seconds = max(
            self.base_backoff_seconds, max_backoff_seconds)
        self._jobs: Dict[str, Job] = {}
        self._queue: List[str] = []
        self._dlq: List[Dict[str, Any]] = []

    def enqueue(self, job_type: str, payload: Dict[str, Any], max_retries: int = 3) -> str:
        job_id = str(uuid.uuid4())
        job = Job(id=job_id, data=JobPayload(job_type=job_type,
                  payload=payload, max_retries=max(0, max_retries)))
        self._jobs[job_id] = job
        self._queue.append(job_id)
        return job_id

    def queue_depth(self) -> int:
        now = time.time()
        return sum(1 for job_id in self._queue if job_id in self._jobs and self._jobs[job_id].available_at <= now)

    def _release_expired_leases(self) -> None:
        now = time.time()
        for job in self._jobs.values():
            if job.lease_owner and job.lease_expires_at and job.lease_expires_at <= now:
                job.lease_owner = None
                job.lease_expires_at = None

    def lease_next(self, worker_id: str) -> Optional[LeasedJob]:
        self._release_expired_leases()
        now = time.time()
        for job_id in list(self._queue):
            job = self._jobs.get(job_id)
            if not job:
                continue
            if job.available_at > now:
                continue
            if job.lease_owner is not None:
                continue

            job.lease_owner = worker_id
            job.lease_expires_at = now + self.lease_seconds
            job.attempts += 1
            return LeasedJob(
                id=job.id,
                job_type=job.data.job_type,
                payload=job.data.payload,
                attempts=job.attempts,
                lease_owner=worker_id,
                lease_expires_at=job.lease_expires_at,
            )
        return None

    def ack(self, job_id: str, worker_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job or job.lease_owner != worker_id:
            return False
        self._jobs.pop(job_id, None)
        self._queue = [j for j in self._queue if j != job_id]
        return True

    def fail(self, job_id: str, worker_id: str, reason: str) -> bool:
        job = self._jobs.get(job_id)
        if not job or job.lease_owner != worker_id:
            return False

        if job.attempts > job.data.max_retries:
            self._dlq.append(
                {
                    "job_id": job.id,
                    "job_type": job.data.job_type,
                    "payload": job.data.payload,
                    "attempts": job.attempts,
                    "reason": reason,
                    "failed_at": time.time(),
                }
            )
            self._jobs.pop(job_id, None)
            self._queue = [j for j in self._queue if j != job_id]
            return True

        backoff = min(self.base_backoff_seconds *
                      (2 ** max(0, job.attempts - 1)), self.max_backoff_seconds)
        job.available_at = time.time() + backoff
        job.lease_owner = None
        job.lease_expires_at = None
        return True

    def dead_letter_queue(self) -> List[Dict[str, Any]]:
        return list(self._dlq)
