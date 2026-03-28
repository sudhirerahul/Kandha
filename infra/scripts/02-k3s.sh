#!/usr/bin/env bash
# 02-k3s.sh — Idempotent K3s installation for Kandha bare-metal nodes
set -euo pipefail

K3S_VERSION="${K3S_VERSION:-v1.31.3+k3s1}"

echo "[02-k3s] Installing K3s ${K3S_VERSION}..."

# Check if K3s is already installed and running (idempotent)
if systemctl is-active --quiet k3s 2>/dev/null; then
  CURRENT_VERSION=$(k3s --version | awk '{print $3}')
  if [[ "${CURRENT_VERSION}" == "${K3S_VERSION}" ]]; then
    echo "[02-k3s] K3s ${K3S_VERSION} already running — skipping install."
    exit 0
  fi
fi

# Install K3s
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="${K3S_VERSION}" sh -s - \
  --disable traefik \
  --write-kubeconfig-mode 644

# Wait for K3s to be ready
echo "[02-k3s] Waiting for K3s to be ready..."
until kubectl get nodes &>/dev/null; do
  sleep 2
done

echo "[02-k3s] K3s installation complete."
echo "[02-k3s] Kubeconfig: /etc/rancher/k3s/k3s.yaml"
