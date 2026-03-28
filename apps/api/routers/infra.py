# infra.py — Infra Configurator router: real K8s manifest generation
from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
import yaml
from fastapi import APIRouter, Depends, HTTPException
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel

from middleware.auth import get_current_user
from services.gmi import GMIClient, get_gmi_client

log = structlog.get_logger()
router = APIRouter(prefix="/infra", tags=["infra"])

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "k8s"
_jinja_env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=False)

# ── Workload presets ─────────────────────────────────────────────────────────

_WORKLOAD_PRESETS: dict[str, dict[str, Any]] = {
    "web": {
        "replicas": 3,
        "port": 3000,
        "memory_request": "256Mi",
        "memory_limit": "512Mi",
        "cpu_request": "100m",
        "cpu_limit": "500m",
        "min_replicas": 2,
        "max_replicas": 10,
    },
    "api": {
        "replicas": 3,
        "port": 8000,
        "memory_request": "256Mi",
        "memory_limit": "512Mi",
        "cpu_request": "200m",
        "cpu_limit": "1000m",
        "min_replicas": 2,
        "max_replicas": 8,
    },
    "ml": {
        "replicas": 1,
        "port": 8080,
        "memory_request": "2Gi",
        "memory_limit": "8Gi",
        "cpu_request": "1000m",
        "cpu_limit": "4000m",
        "min_replicas": 1,
        "max_replicas": 4,
    },
    "database_heavy": {
        "replicas": 1,
        "port": 5432,
        "memory_request": "1Gi",
        "memory_limit": "4Gi",
        "cpu_request": "500m",
        "cpu_limit": "2000m",
        "min_replicas": 1,
        "max_replicas": 3,
    },
    "mixed": {
        "replicas": 2,
        "port": 8000,
        "memory_request": "512Mi",
        "memory_limit": "1Gi",
        "cpu_request": "250m",
        "cpu_limit": "1000m",
        "min_replicas": 2,
        "max_replicas": 6,
    },
}

_PROVIDER_TEMPLATES: dict[str, dict[str, str]] = {
    "hetzner": {"region": "fsn1", "cluster_type": "k3s"},
    "ovh": {"region": "gra", "cluster_type": "k3s"},
    "on-prem": {"region": "local", "cluster_type": "k3s"},
}


# ── Pydantic schemas ─────────────────────────────────────────────────────────

class InfraGenerateRequest(BaseModel):
    """Request to generate K8s manifests."""
    provider: str = "hetzner"
    workload: str = "web"
    size: str = "medium"
    app_name: str = "my-app"
    domain: str | None = None
    services: list[str] | None = None


class ManifestItem(BaseModel):
    """A single K8s manifest."""
    kind: str
    name: str
    yaml: str


class InfraGenerateResponse(BaseModel):
    """Generated infrastructure configuration."""
    manifests: list[ManifestItem]
    helm_values: dict[str, Any]
    setup_script: str
    provider: str
    workload: str
    ai_customizations: str | None = None


class InfraValidateRequest(BaseModel):
    """Request to validate K8s YAML."""
    yaml_content: str


class InfraValidateResponse(BaseModel):
    """Validation result."""
    valid: bool
    errors: list[str]
    warnings: list[str]


class TemplatePreset(BaseModel):
    """Available template preset."""
    name: str
    description: str
    workload: str
    replicas: int
    memory: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def _render_template(name: str, ctx: dict[str, Any]) -> str:
    """Render a Jinja2 K8s template."""
    template = _jinja_env.get_template(name)
    return template.render(**ctx)


def _generate_manifests(req: InfraGenerateRequest) -> list[ManifestItem]:
    """Generate K8s manifests from templates + workload presets."""
    preset = _WORKLOAD_PRESETS.get(req.workload, _WORKLOAD_PRESETS["web"])

    ctx = {
        "app_name": req.app_name,
        "namespace": f"{req.app_name}-ns",
        "domain": req.domain,
        "image": f"ghcr.io/{req.app_name}:latest",
        **preset,
    }

    manifests = []

    # Namespace
    manifests.append(ManifestItem(
        kind="Namespace",
        name=f"{req.app_name}-ns",
        yaml=_render_template("namespace.yaml.j2", ctx),
    ))

    # Deployment
    manifests.append(ManifestItem(
        kind="Deployment",
        name=req.app_name,
        yaml=_render_template("deployment.yaml.j2", ctx),
    ))

    # Service
    manifests.append(ManifestItem(
        kind="Service",
        name=req.app_name,
        yaml=_render_template("service.yaml.j2", ctx),
    ))

    # Ingress (only if domain provided)
    if req.domain:
        manifests.append(ManifestItem(
            kind="Ingress",
            name=req.app_name,
            yaml=_render_template("ingress.yaml.j2", ctx),
        ))

    # HPA
    manifests.append(ManifestItem(
        kind="HorizontalPodAutoscaler",
        name=req.app_name,
        yaml=_render_template("hpa.yaml.j2", ctx),
    ))

    return manifests


def _generate_helm_values(req: InfraGenerateRequest) -> dict[str, Any]:
    """Generate Helm values override for the deployment."""
    preset = _WORKLOAD_PRESETS.get(req.workload, _WORKLOAD_PRESETS["web"])
    provider_cfg = _PROVIDER_TEMPLATES.get(req.provider, _PROVIDER_TEMPLATES["hetzner"])

    return {
        "replicaCount": preset["replicas"],
        "image": {"repository": f"ghcr.io/{req.app_name}", "tag": "latest"},
        "service": {"type": "ClusterIP", "port": preset["port"]},
        "resources": {
            "requests": {"memory": preset["memory_request"], "cpu": preset["cpu_request"]},
            "limits": {"memory": preset["memory_limit"], "cpu": preset["cpu_limit"]},
        },
        "autoscaling": {
            "enabled": True,
            "minReplicas": preset.get("min_replicas", 1),
            "maxReplicas": preset.get("max_replicas", 5),
            "targetCPUUtilizationPercentage": 70,
        },
        "ingress": {"enabled": bool(req.domain), "host": req.domain or ""},
        "provider": req.provider,
        "region": provider_cfg["region"],
        "clusterType": provider_cfg["cluster_type"],
    }


def _generate_setup_script(req: InfraGenerateRequest) -> str:
    """Generate a setup script for the deployment."""
    provider_cfg = _PROVIDER_TEMPLATES.get(req.provider, _PROVIDER_TEMPLATES["hetzner"])
    cluster_type = provider_cfg["cluster_type"]

    return f"""#!/bin/bash
# Kandha — Auto-generated setup script for {req.provider} ({req.workload} workload)
# Generated by Kandha Infra Configurator
set -euo pipefail

echo "=== Kandha Infrastructure Setup ==="
echo "Provider: {req.provider}"
echo "Workload: {req.workload}"
echo "Cluster:  {cluster_type}"

# 1. Install K3s (lightweight Kubernetes)
if ! command -v kubectl &>/dev/null; then
    echo "Installing K3s..."
    curl -sfL https://get.k3s.io | sh -
    mkdir -p ~/.kube
    sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
    sudo chown $(id -u):$(id -g) ~/.kube/config
    echo "K3s installed."
else
    echo "kubectl already available, skipping K3s install."
fi

# 2. Apply manifests
echo "Applying Kubernetes manifests..."
kubectl apply -f namespace.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
{"kubectl apply -f ingress.yaml" if req.domain else "# No ingress (no domain configured)"}
kubectl apply -f hpa.yaml

# 3. Verify
echo "Waiting for deployment to be ready..."
kubectl -n {req.app_name}-ns rollout status deployment/{req.app_name} --timeout=120s

echo ""
echo "=== Deployment Complete ==="
kubectl -n {req.app_name}-ns get pods
echo ""
echo "Your app is running on {req.provider}!"
"""


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/generate", response_model=InfraGenerateResponse, status_code=201)
async def generate_infra(
    body: InfraGenerateRequest,
    gmi: GMIClient = Depends(get_gmi_client),
    user_id: str = Depends(get_current_user),
) -> InfraGenerateResponse:
    """Generate K8s manifests, Helm values, and setup script for the configured workload."""
    if body.workload not in _WORKLOAD_PRESETS:
        raise HTTPException(status_code=422, detail=f"Unknown workload type: {body.workload}")
    if body.provider not in _PROVIDER_TEMPLATES:
        raise HTTPException(status_code=422, detail=f"Unknown provider: {body.provider}")

    log.info(
        "infra.generate.started",
        provider=body.provider,
        workload=body.workload,
        user_id=user_id,
    )

    # Generate base manifests from templates
    manifests = _generate_manifests(body)
    helm_values = _generate_helm_values(body)
    setup_script = _generate_setup_script(body)

    # Ask Kimi K2 to review and suggest customizations
    ai_customizations: str | None = None
    try:
        manifest_yaml = "\n---\n".join(m.yaml for m in manifests)
        review_prompt = (
            f"Review these K8s manifests for a {body.workload} workload on {body.provider}. "
            f"In 2-3 sentences, suggest specific improvements for production readiness "
            f"(security contexts, pod disruption budgets, network policies). Be concise.\n\n"
            f"```yaml\n{manifest_yaml[:2000]}\n```"
        )
        ai_customizations = await gmi.complete(
            [{"role": "user", "content": review_prompt}],
            temperature=0.2,
            max_tokens=300,
        )
    except Exception as exc:
        log.warning("infra.ai_review.failed", error=str(exc))

    log.info("infra.generate.complete", manifests=len(manifests), user_id=user_id)

    return InfraGenerateResponse(
        manifests=manifests,
        helm_values=helm_values,
        setup_script=setup_script,
        provider=body.provider,
        workload=body.workload,
        ai_customizations=ai_customizations,
    )


@router.get("/templates", response_model=list[TemplatePreset])
async def list_templates() -> list[TemplatePreset]:
    """Return available workload template presets."""
    return [
        TemplatePreset(
            name=name,
            description=f"{name.replace('_', ' ').title()} workload preset",
            workload=name,
            replicas=preset["replicas"],
            memory=preset["memory_limit"],
        )
        for name, preset in _WORKLOAD_PRESETS.items()
    ]


@router.post("/validate", response_model=InfraValidateResponse)
async def validate_manifests(body: InfraValidateRequest) -> InfraValidateResponse:
    """Validate K8s YAML syntax and check for common issues."""
    errors: list[str] = []
    warnings: list[str] = []

    try:
        docs = list(yaml.safe_load_all(body.yaml_content))
    except yaml.YAMLError as exc:
        return InfraValidateResponse(valid=False, errors=[f"YAML parse error: {exc}"], warnings=[])

    if not docs:
        return InfraValidateResponse(valid=False, errors=["No YAML documents found."], warnings=[])

    for i, doc in enumerate(docs):
        if not isinstance(doc, dict):
            errors.append(f"Document {i + 1}: not a valid K8s manifest (expected mapping).")
            continue

        # Check required fields
        if "apiVersion" not in doc:
            errors.append(f"Document {i + 1}: missing 'apiVersion'.")
        if "kind" not in doc:
            errors.append(f"Document {i + 1}: missing 'kind'.")
        if "metadata" not in doc:
            errors.append(f"Document {i + 1}: missing 'metadata'.")
        elif not doc["metadata"].get("name"):
            errors.append(f"Document {i + 1}: missing 'metadata.name'.")

        # Warnings for best practices
        kind = doc.get("kind", "")
        if kind == "Deployment":
            spec = doc.get("spec", {}).get("template", {}).get("spec", {})
            containers = spec.get("containers", [])
            for c in containers:
                if not c.get("resources"):
                    warnings.append(f"Document {i + 1}: container '{c.get('name')}' has no resource limits.")
                if not c.get("livenessProbe"):
                    warnings.append(f"Document {i + 1}: container '{c.get('name')}' has no liveness probe.")

    return InfraValidateResponse(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


@router.get("/ping")
async def ping() -> dict[str, str]:
    """Health check for the infra router."""
    return {"router": "infra", "status": "ok"}
