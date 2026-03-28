#!/usr/bin/env bash
# 01-base.sh — Idempotent base system setup for Kandha bare-metal nodes
set -euo pipefail

echo "[01-base] Starting base system setup..."

# Update package index (idempotent)
apt-get update -qq

# Install required packages (idempotent via apt)
PACKAGES=(
  curl
  wget
  git
  htop
  ufw
  fail2ban
  unattended-upgrades
  ca-certificates
  gnupg
  lsb-release
)
apt-get install -y --no-install-recommends "${PACKAGES[@]}"

# Configure UFW firewall (idempotent)
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "[01-base] Base setup complete."
