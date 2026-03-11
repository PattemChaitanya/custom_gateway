# Mini-Cloud Platform Contract (v1)

## Guarantees

- Service registration: instances are registered in a registry with metadata and routing weight.
- Discovery health: heartbeat updates liveness; TTL expiry removes stale instances.
- Routing: only healthy, non-expired instances receive traffic.
- Baseline auth and rate policies: routes reference externally configured policy objects.
- Observability: request IDs, structured request logs, and RED metrics are emitted.
- Scaling simulation: autoscaler evaluates queue depth and p95 latency with cooldown and hysteresis.
- State durability: control-plane state is snapshotted on shutdown and restored on startup.

## Tradeoffs

- Upfront contract work delays coding by 1-2 days but minimizes repeated redesign.
- Additional control-plane state (registry/scheduler/scaler) increases complexity but improves reliability.
- Tight coupling between discovery and routing accelerates end-to-end validation and failover testing.

## Invariants

- Expired instance never receives traffic.
- Unhealthy instance never receives traffic.
- Scheduler retries with backoff and sends exhausted jobs to DLQ.
- Autoscaler never breaches min/max replicas.
- Autoscaler ignores contradictory short spikes during cooldown.

## SLO-style checks (simulation)

- Routing availability for healthy services: >= 99% in failure-injection runs.
- Route error ratio for healthy services: <= 1% under normal traffic profile.
- Scheduler lease recovery: crashed worker jobs are re-leaseable after lease expiry.

## Operational Controls

- Snapshot state: `POST /mini-cloud/control-loop/snapshot`
- Restore state: `POST /mini-cloud/control-loop/restore`
- Force one loop iteration: `POST /mini-cloud/control-loop/tick`
- Inspect loop status: `GET /mini-cloud/control-loop/status`
- Reset runtime state for tests: `POST /mini-cloud/reset`

## Routing Strategies

- `round_robin`: cycles across all routable instances.
- `weighted`: probabilistic weighted selection.
- `weighted_round_robin`: deterministic weighted rotation.
