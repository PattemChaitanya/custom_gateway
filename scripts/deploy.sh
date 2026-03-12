#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# EC2 Deployment Script
# Called by the GitHub Actions deploy job after images are pushed to GHCR.
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Required environment variables ──────────────────────────────────────────
: "${DOCKER_REGISTRY:?DOCKER_REGISTRY is required}"
: "${BACKEND_IMAGE:?BACKEND_IMAGE is required}"
: "${FRONTEND_IMAGE:?FRONTEND_IMAGE is required}"
: "${IMAGE_TAG:?IMAGE_TAG is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${REDIS_PASSWORD:?REDIS_PASSWORD is required}"
: "${SECRET_KEY:?SECRET_KEY is required}"
: "${FIRST_SUPERUSER_PASSWORD:?FIRST_SUPERUSER_PASSWORD is required}"

COMPOSE_FILE="docker-compose.prod.yml"
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Deploying Gateway Management (tag: ${IMAGE_TAG})"
cd "$APP_DIR"

# ── Log in to GHCR (uses a token file written by the CI/CD pipeline, or
#    falls back to docker's existing credentials) ────────────────────────────
if [ -n "${GHCR_TOKEN:-}" ]; then
  echo "$GHCR_TOKEN" | docker login ghcr.io -u "${GHCR_USER:-github}" --password-stdin
fi

# ── Pull the new images ────────────────────────────────────────────────────
echo "==> Pulling images …"
docker pull "${DOCKER_REGISTRY}/${BACKEND_IMAGE}:${IMAGE_TAG}"
docker pull "${DOCKER_REGISTRY}/${FRONTEND_IMAGE}:${IMAGE_TAG}"

# ── Export variables for docker compose interpolation ───────────────────────
export DOCKER_REGISTRY BACKEND_IMAGE FRONTEND_IMAGE IMAGE_TAG
export POSTGRES_PASSWORD REDIS_PASSWORD SECRET_KEY FIRST_SUPERUSER_PASSWORD
export POSTGRES_DB="${POSTGRES_DB:-gateway}"
export POSTGRES_USER="${POSTGRES_USER:-gateway}"
export ENCRYPTION_KEY="${ENCRYPTION_KEY:-}"
export ENCRYPTION_SALT="${ENCRYPTION_SALT:-gateway-salt}"
export FIRST_SUPERUSER_EMAIL="${FIRST_SUPERUSER_EMAIL:-admin@example.com}"
export APP_PORT="${APP_PORT:-80}"

# ── Roll out ────────────────────────────────────────────────────────────────
echo "==> Starting services …"
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

# ── Wait for health checks ─────────────────────────────────────────────────
echo "==> Waiting for services to become healthy …"
TIMEOUT=120
ELAPSED=0
while [ "$ELAPSED" -lt "$TIMEOUT" ]; do
  HEALTHY=$(docker compose -f "$COMPOSE_FILE" ps --format json | \
    python3 -c "
import sys, json
lines = sys.stdin.read().strip().split('\n')
services = [json.loads(l) for l in lines if l]
healthy = all(s.get('Health','') == 'healthy' or s.get('State','') == 'running' for s in services)
print('yes' if healthy else 'no')
" 2>/dev/null || echo "no")

  if [ "$HEALTHY" = "yes" ]; then
    echo "==> All services healthy!"
    break
  fi
  sleep 5
  ELAPSED=$((ELAPSED + 5))
done

if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
  echo "WARNING: Timed out waiting for services to become healthy."
  docker compose -f "$COMPOSE_FILE" ps
  docker compose -f "$COMPOSE_FILE" logs --tail=30
  exit 1
fi

# ── Prune old images to free disk space ─────────────────────────────────────
echo "==> Pruning unused Docker images …"
docker image prune -af --filter "until=168h"

echo "==> Deployment complete!"
