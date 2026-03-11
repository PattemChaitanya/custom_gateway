import time

from app.control_plane.discovery import ServiceRegistry


def test_registry_expires_stale_instances():
    registry = ServiceRegistry()
    registry.register_instance(
        "orders", "i-1", "http://orders-1", ttl_seconds=1)

    instances = registry.list_instances("orders")
    assert len(instances) == 1

    time.sleep(1.1)
    expired = registry.expire_instances()

    assert "orders:i-1" in expired
    assert registry.list_instances("orders") == []


def test_route_selects_only_healthy_instances():
    registry = ServiceRegistry()
    registry.register_instance(
        "billing", "i-1", "http://billing-1", ttl_seconds=30)
    registry.register_instance(
        "billing", "i-2", "http://billing-2", ttl_seconds=30)
    registry.mark_health("billing", "i-2", healthy=False)

    selected = [registry.select_instance(
        "billing", strategy="round_robin") for _ in range(3)]

    assert all(item is not None for item in selected)
    assert all(item.instance_id == "i-1" for item in selected)


def test_weighted_selection_biases_heavier_instance():
    registry = ServiceRegistry()
    registry.register_instance(
        "inventory", "i-light", "http://inv-1", weight=1)
    registry.register_instance(
        "inventory", "i-heavy", "http://inv-2", weight=5)

    picks = [registry.select_instance(
        "inventory", strategy="weighted").instance_id for _ in range(200)]

    assert picks.count("i-heavy") > picks.count("i-light")


def test_health_status_transitions_affect_routability():
    registry = ServiceRegistry()
    registry.register_instance("search", "s-1", "http://search-1")

    assert registry.set_health_status("search", "s-1", "degraded") is True
    assert registry.select_instance("search") is not None

    assert registry.set_health_status("search", "s-1", "unhealthy") is True
    assert registry.select_instance("search") is None


def test_heartbeat_with_health_status_updates_state():
    registry = ServiceRegistry()
    registry.register_instance("profile", "p-1", "http://profile-1")

    updated = registry.heartbeat("profile", "p-1", health_status="unknown")
    assert updated is not None
    assert updated.health_status == "unknown"
    assert updated.healthy is False
