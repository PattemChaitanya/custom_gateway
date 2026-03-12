#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# EC2 Instance Setup Script
# Run this ONCE on a fresh EC2 instance (Amazon Linux 2023 / Ubuntu 22.04+)
# to install Docker, Docker Compose, and configure the system for deployments.
#
# Usage:  chmod +x scripts/ec2-setup.sh && sudo ./scripts/ec2-setup.sh
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

echo "==> Detecting OS …"
if [ -f /etc/os-release ]; then
  . /etc/os-release
  OS_ID="$ID"
else
  echo "Cannot detect OS"; exit 1
fi

# ── Install Docker ──────────────────────────────────────────────────────────
install_docker_ubuntu() {
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
}

install_docker_amzn() {
  dnf update -y
  dnf install -y docker
  systemctl start docker
  systemctl enable docker
  # Install compose plugin
  DOCKER_CONFIG=${DOCKER_CONFIG:-/usr/local/lib/docker}
  mkdir -p "$DOCKER_CONFIG/cli-plugins"
  COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep tag_name | cut -d\" -f4)
  curl -SL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-$(uname -m)" \
    -o "$DOCKER_CONFIG/cli-plugins/docker-compose"
  chmod +x "$DOCKER_CONFIG/cli-plugins/docker-compose"
}

case "$OS_ID" in
  ubuntu|debian)  install_docker_ubuntu ;;
  amzn|al)        install_docker_amzn ;;
  *)              echo "Unsupported OS: $OS_ID. Install Docker manually."; exit 1 ;;
esac

# ── Post-install: let the deploy user run Docker without sudo ──────────────
DEPLOY_USER="${SUDO_USER:-ec2-user}"
if id "$DEPLOY_USER" &>/dev/null; then
  usermod -aG docker "$DEPLOY_USER"
  echo "==> Added $DEPLOY_USER to docker group (re-login required)."
fi

# ── Create app directory ───────────────────────────────────────────────────
APP_DIR="/home/${DEPLOY_USER}/gateway"
mkdir -p "$APP_DIR/scripts"
chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "$APP_DIR"

# ── Verify installation ───────────────────────────────────────────────────
docker --version
docker compose version

echo ""
echo "==> EC2 setup complete!"
echo "    - Log out and back in for docker group changes to take effect."
echo "    - App directory: $APP_DIR"
echo ""
echo "Required GitHub Secrets for deployment:"
echo "  EC2_HOST             – Public IP or hostname of this instance"
echo "  EC2_USER             – SSH user (e.g., ubuntu or ec2-user)"
echo "  EC2_SSH_KEY          – Private SSH key for this instance"
echo "  POSTGRES_PASSWORD    – Database password"
echo "  REDIS_PASSWORD       – Redis password"
echo "  SECRET_KEY           – Application secret key"
echo "  FIRST_SUPERUSER_PASSWORD – Initial admin password"
