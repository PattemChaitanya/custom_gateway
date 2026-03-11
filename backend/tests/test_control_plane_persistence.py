import json

from app.control_plane.runtime import (
    autoscaler,
    registry,
    restore_state,
    scheduler,
    set_simulated_latency,
    snapshot_state,
)


def test_snapshot_and_restore_control_plane_state(tmp_path):
    state_file = tmp_path / "cp_state.json"

    # Seed runtime state.
    registry.register_instance(
        "persist", "p-1", "http://persist-1", ttl_seconds=60, weight=3)
    registry.mark_health("persist", "p-1", healthy=False)
    job_id = scheduler.enqueue("persist_job", {"k": "v"}, max_retries=4)
    autoscaler.current_replicas = 4
    set_simulated_latency(777)

    snap = snapshot_state(str(state_file))
    assert snap["path"] == str(state_file)

    # Corrupt in-memory state and restore from snapshot.
    registry._services.clear()  # noqa: SLF001
    scheduler._jobs.clear()  # noqa: SLF001
    scheduler._queue.clear()  # noqa: SLF001
    autoscaler.current_replicas = 1
    set_simulated_latency(1)

    restored = restore_state(str(state_file))
    assert restored["restored"] is True

    instances = registry.list_instances("persist")
    assert len(instances) == 1
    assert instances[0].instance_id == "p-1"
    assert instances[0].healthy is False

    assert job_id in scheduler._jobs  # noqa: SLF001
    assert autoscaler.current_replicas == 4

    payload = json.loads(state_file.read_text(encoding="utf-8"))
    assert payload["version"] == "control-plane-state/v1"
