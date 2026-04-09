"""
instance_manager.py — Per-account Docker gateway runtime provisioner.

Responsibilities:
  - find_free_port()       Find an unused port in 5000–5999
  - provision_instance()   Spawn a gateway-runtime container for an account
  - deprovision_instance() Stop + remove a container, mark instance expired/stopped
  - get_instance()         Fetch the live Instance row for an account

Provisioning flow (T2.1 → T2.5):
  1. find_free_port()   — scan 5000–5999, skip ports already in instances table
  2. docker.run()       — launch gateway-runtime image with required env vars
  3. poll_health()      — GET /internal/health until 200 (max 30s)
  4. write Instance row — status=running, expires_at=now+48h
  5. on any failure     — rollback: stop+remove container, delete Instance row

On success returns ProvisionResult(gateway_url, container_id, port, expires_at).
"""

import asyncio
import logging
import os
import secrets
import socket
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Optional

import docker
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Instance
from app.storage.tiered_store import get_store

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
GATEWAY_IMAGE = os.getenv("GATEWAY_IMAGE", "flowgate-gateway-runtime:latest")
GATEWAY_PORT_RANGE_START = 5000
GATEWAY_PORT_RANGE_END = 5999
DOCKER_NETWORK = os.getenv("GATEWAY_DOCKER_NETWORK", "flowgate_net")
CONTROL_PLANE_URL = os.getenv("CONTROL_PLANE_URL", "http://backend:8000")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
INSTANCE_TTL_HOURS = 48
HEALTH_POLL_TIMEOUT_S = 30
HEALTH_POLL_INTERVAL_S = 1


@dataclass
class ProvisionResult:
    gateway_url: str
    container_id: str
    port: int
    expires_at: datetime
    account_secret: str


# ── Port finder (T2.1) ────────────────────────────────────────────────────────

async def find_free_port(db: AsyncSession) -> int:
    """Return the first port in 5000–5999 not already in use in DB or on the host."""
    # Ports already claimed in DB (running or provisioning)
    result = await db.execute(
        select(Instance.port).where(
            Instance.status.in_(["provisioning", "running"])
        )
    )
    used_ports = {row[0] for row in result.all()}

    for port in range(GATEWAY_PORT_RANGE_START, GATEWAY_PORT_RANGE_END + 1):
        if port in used_ports:
            continue
        # Double-check at OS level (another process might hold it)
        if _port_is_free(port):
            return port

    raise RuntimeError("No free ports available in range 5000–5999")


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.1)
        return s.connect_ex(("127.0.0.1", port)) != 0


# ── Docker runner (T2.2) ──────────────────────────────────────────────────────

def _docker_client() -> docker.DockerClient:
    return docker.from_env()


def _run_container(account_id: int, port: int, account_secret: str) -> str:
    """Synchronous Docker run — called in a thread executor to stay non-blocking."""
    client = _docker_client()

    container = client.containers.run(
        image=GATEWAY_IMAGE,
        name=f"gateway-{account_id}",
        detach=True,
        network=DOCKER_NETWORK,
        ports={f"{port}/tcp": port},
        environment={
            "ACCOUNT_ID": str(account_id),
            "GATEWAY_PORT": str(port),
            "REDIS_URL": REDIS_URL,
            "CONTROL_PLANE_URL": CONTROL_PLANE_URL,
            "ACCOUNT_SECRET": account_secret,
            "SQLITE_PATH": "/data/gateway.db",
        },
        volumes={
            f"gateway_data_{account_id}": {"bind": "/data", "mode": "rw"},
        },
        restart_policy={"Name": "unless-stopped"},
    )
    return container.id  # type: ignore[return-value]


def _stop_container(container_id: str) -> None:
    """Stop and remove a container. Ignores errors (best-effort cleanup)."""
    try:
        client = _docker_client()
        c = client.containers.get(container_id)
        c.stop(timeout=10)
        c.remove(force=True)
    except Exception as exc:
        logger.warning("Could not stop/remove container %s: %s", container_id, exc)


# ── Health poller (T2.3) ──────────────────────────────────────────────────────

async def _poll_health(port: int, timeout_s: int = HEALTH_POLL_TIMEOUT_S) -> None:
    """Poll GET http://localhost:{port}/internal/health until 200 or timeout."""
    url = f"http://localhost:{port}/internal/health"
    deadline = asyncio.get_event_loop().time() + timeout_s

    async with httpx.AsyncClient(timeout=2.0) as client:
        while asyncio.get_event_loop().time() < deadline:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    logger.info("Gateway on port %d is healthy", port)
                    return
            except (httpx.ConnectError, httpx.ReadTimeout):
                pass
            await asyncio.sleep(HEALTH_POLL_INTERVAL_S)

    raise TimeoutError(
        f"Gateway on port {port} did not become healthy within {timeout_s}s"
    )


# ── Main provisioner (T2, T2.4, T2.5) ────────────────────────────────────────

async def provision_instance(account_id: int, db: AsyncSession) -> ProvisionResult:
    """
    Full provisioning flow for a new account gateway instance.

    Steps:
      1. Find a free port
      2. Insert Instance row with status=provisioning (reserve the port)
      3. Run Docker container
      4. Poll /internal/health
      5. Update Instance row to status=running with container_id
      6. On ANY failure → rollback (delete Instance row, stop container)
    """
    port = await find_free_port(db)
    account_secret = secrets.token_hex(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=INSTANCE_TTL_HOURS)
    gateway_url = f"http://localhost:{port}"

    # Step 2 — Reserve port in DB (status=provisioning)
    instance = Instance(
        account_id=account_id,
        port=port,
        status="provisioning",
        gateway_url=gateway_url,
        expires_at=expires_at,
    )
    db.add(instance)
    await db.commit()
    await db.refresh(instance)

    container_id: Optional[str] = None

    try:
        # Step 3 — Launch container (blocking Docker call off event loop)
        loop = asyncio.get_event_loop()
        container_id = await loop.run_in_executor(
            None, _run_container, account_id, port, account_secret
        )
        logger.info("Started container %s for account %d on port %d", container_id, account_id, port)

        # Step 4 — Wait for health
        await _poll_health(port)

        # Step 5 — Mark running
        instance.container_id = container_id
        instance.status = "running"
        await db.commit()
        await db.refresh(instance)

        # Write-through to tiered store (L1+L2) so hot-path reads skip the DB
        await get_store().put("instance", str(instance.account_id), {
            "id": instance.id,
            "account_id": instance.account_id,
            "container_id": container_id,
            "port": port,
            "status": "running",
            "gateway_url": gateway_url,
            "expires_at": expires_at.isoformat(),
        })

        return ProvisionResult(
            gateway_url=gateway_url,
            container_id=container_id,
            port=port,
            expires_at=expires_at,
            account_secret=account_secret,
        )

    except Exception as exc:
        logger.error("Provisioning failed for account %d: %s — rolling back", account_id, exc)
        # Step 6 — Rollback
        await _rollback(db, instance, container_id)
        raise


async def _rollback(
    db: AsyncSession,
    instance: Instance,
    container_id: Optional[str],
) -> None:
    """Remove Instance DB row and stop Docker container on provisioning failure."""
    try:
        await db.delete(instance)
        await db.commit()
    except Exception as exc:
        logger.error("Failed to delete instance row during rollback: %s", exc)

    if container_id:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _stop_container, container_id)


# ── Deprovisioner ─────────────────────────────────────────────────────────────

async def deprovision_instance(
    instance: Instance,
    db: AsyncSession,
    new_status: str = "stopped",
) -> None:
    """Stop + remove the Docker container and update the instance status."""
    container_id = instance.container_id
    if container_id:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _stop_container, container_id)

    instance.status = new_status
    await db.commit()

    # Invalidate / update tiered store
    store = get_store()
    if new_status in ("expired", "stopped"):
        await store.delete("instance", str(instance.account_id))
    else:
        await store.put("instance", str(instance.account_id), {
            "id": instance.id,
            "account_id": instance.account_id,
            "container_id": instance.container_id,
            "port": instance.port,
            "status": new_status,
            "gateway_url": instance.gateway_url,
            "expires_at": instance.expires_at.isoformat() if instance.expires_at else None,
        })

    logger.info(
        "Deprovisioned instance id=%d account=%d status=%s",
        instance.id, instance.account_id, new_status,
    )


# ── Getter ────────────────────────────────────────────────────────────────────

async def get_instance(account_id: int, db: AsyncSession) -> Optional[Instance]:
    """Return the Instance row for an account, or None if not yet provisioned."""
    result = await db.execute(
        select(Instance).where(Instance.account_id == account_id)
    )
    return result.scalar_one_or_none()
