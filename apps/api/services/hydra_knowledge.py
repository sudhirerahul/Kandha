# hydra_knowledge.py — Upload Kandha infrastructure knowledge base to HydraDB for RAG
#
# Uploads curated knowledge about bare-metal pricing, migration best practices,
# and K3s setup guides so the repatriation agent can ground its advice in facts.
#
# Usage:  python -m services.hydra_knowledge
from __future__ import annotations

import asyncio
import sys

import httpx
import structlog

from config import get_settings

log = structlog.get_logger()

# ── Knowledge entries ────────────────────────────────────────────────────────

KNOWLEDGE_ENTRIES: list[dict[str, str]] = [
    # Hetzner dedicated server pricing (as of 2025)
    {
        "title": "Hetzner AX42 Pricing & Specs",
        "content": (
            "Hetzner AX42: $58/month. AMD Ryzen 7 7700 (8 cores / 16 threads), "
            "64 GB DDR5 ECC RAM, 2x 512 GB NVMe SSD (software RAID), "
            "unlimited traffic at 1 Gbit/s. Ideal for small-to-medium K3s clusters, "
            "CI/CD runners, and development environments."
        ),
    },
    {
        "title": "Hetzner AX102 Pricing & Specs",
        "content": (
            "Hetzner AX102: $94/month. AMD Ryzen 9 7950X3D (16 cores / 32 threads), "
            "128 GB DDR5 ECC RAM, 2x 1 TB NVMe SSD (software RAID), "
            "unlimited traffic at 1 Gbit/s. Good for production K3s/K8s clusters, "
            "database workloads, and multi-tenant SaaS backends."
        ),
    },
    {
        "title": "Hetzner AX162 Pricing & Specs",
        "content": (
            "Hetzner AX162: $136/month. AMD EPYC 9454P (48 cores / 96 threads), "
            "256 GB DDR5 ECC RAM, 2x 2 TB NVMe SSD (software RAID), "
            "unlimited traffic at 1 Gbit/s. Best for heavy production workloads, "
            "ML inference, large databases, and high-traffic applications."
        ),
    },
    # Migration checklists
    {
        "title": "Cloud Repatriation Pre-Migration Checklist",
        "content": (
            "Before migrating off AWS/GCP/Azure: "
            "1. Audit all managed services in use (RDS, Lambda, SQS, etc.) and identify self-hosted replacements. "
            "2. Map egress traffic patterns — high egress is often the biggest hidden cost. "
            "3. Inventory IAM roles and secrets — plan Vault or SOPS for bare metal. "
            "4. Document DNS and CDN setup — move to Cloudflare or self-hosted Traefik. "
            "5. Identify stateful vs stateless services — stateless moves first. "
            "6. Test backup and restore procedures before cutting over. "
            "7. Plan a rollback window of at least 2 weeks with dual-running environments."
        ),
    },
    {
        "title": "Migration Best Practices",
        "content": (
            "Best practices for cloud-to-bare-metal migration: "
            "- Migrate stateless services first (API servers, workers). "
            "- Use blue-green deployment: run both environments in parallel. "
            "- Move databases last after validating replication lag. "
            "- Replace managed Kubernetes (EKS/GKE) with K3s for <50 node clusters. "
            "- Replace S3 with MinIO (S3-compatible, self-hosted). "
            "- Replace RDS with PostgreSQL on dedicated NVMe storage. "
            "- Replace ElastiCache with self-hosted Redis or KeyDB. "
            "- Monitor cost savings weekly during the transition period."
        ),
    },
    # K3s setup
    {
        "title": "K3s Quick Setup Guide",
        "content": (
            "K3s single-node install: curl -sfL https://get.k3s.io | sh - "
            "Multi-node: install server first, then join agents with "
            "curl -sfL https://get.k3s.io | K3S_URL=https://<server>:6443 K3S_TOKEN=<token> sh -. "
            "K3s includes Traefik ingress, CoreDNS, and local-path storage by default. "
            "For production: disable default Traefik (--disable=traefik) and install "
            "NGINX Ingress or Traefik v2 via Helm for more control. "
            "Add --cluster-init for embedded etcd HA (3+ server nodes recommended). "
            "Resource requirements: 512 MB RAM minimum per node, 1 CPU core."
        ),
    },
    {
        "title": "K3s Production Hardening",
        "content": (
            "Production K3s hardening steps: "
            "1. Enable secrets encryption: --secrets-encryption flag on server. "
            "2. Use external etcd or embedded etcd HA (3 server nodes). "
            "3. Set up cert-manager for automatic TLS certificates. "
            "4. Install Prometheus + Grafana via kube-prometheus-stack Helm chart. "
            "5. Configure PodSecurityStandards (restricted profile). "
            "6. Set resource requests/limits on all workloads. "
            "7. Use NetworkPolicies to isolate namespaces. "
            "8. Automated backups with Velero or etcd snapshots."
        ),
    },
]


async def upload_knowledge() -> None:
    """Upload all knowledge entries to HydraDB via POST /upload/knowledge."""
    settings = get_settings()
    base_url = settings.hydra_base_url.rstrip("/") if settings.hydra_base_url else None
    api_key = settings.hydra_api_key
    tenant_id = settings.hydra_tenant_id

    if not base_url or not api_key:
        log.warning("hydra_knowledge.skipped", reason="HYDRA_BASE_URL or HYDRA_API_KEY not configured")
        return

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    uploaded = 0
    failed = 0

    async with httpx.AsyncClient(timeout=15.0) as client:
        for entry in KNOWLEDGE_ENTRIES:
            payload = {
                "tenant_id": tenant_id,
                "title": entry["title"],
                "content": entry["content"],
                "metadata": {"source": "kandha_knowledge_base", "category": "infrastructure"},
            }
            try:
                resp = await client.post(f"{base_url}/upload/knowledge", headers=headers, json=payload)
                resp.raise_for_status()
                uploaded += 1
                log.info("hydra_knowledge.uploaded", title=entry["title"])
            except httpx.HTTPStatusError as exc:
                failed += 1
                log.error(
                    "hydra_knowledge.upload_failed",
                    title=entry["title"],
                    status=exc.response.status_code,
                    detail=exc.response.text[:200],
                )
            except httpx.RequestError as exc:
                failed += 1
                log.error("hydra_knowledge.request_error", title=entry["title"], error=str(exc))

    log.info("hydra_knowledge.done", uploaded=uploaded, failed=failed, total=len(KNOWLEDGE_ENTRIES))


def main() -> None:
    """CLI entrypoint."""
    print(f"Uploading {len(KNOWLEDGE_ENTRIES)} knowledge entries to HydraDB...")
    asyncio.run(upload_knowledge())
    print("Done.")


if __name__ == "__main__":
    main()
