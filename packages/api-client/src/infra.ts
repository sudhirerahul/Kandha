// infra.ts — Typed client for /infra endpoints (K8s manifest & Helm values generation)
import type { InfraConfig, K8sManifest, DeploymentStatus } from "@kandha/types";

export interface InfraClientConfig {
  baseUrl: string;
  token?: string;
}

function headers(token?: string): HeadersInit {
  const h: HeadersInit = { "Content-Type": "application/json" };
  if (token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

export async function generateManifests(
  infraConfig: InfraConfig,
  config: InfraClientConfig
): Promise<K8sManifest> {
  const res = await fetch(`${config.baseUrl}/infra/manifests`, {
    method: "POST",
    headers: headers(config.token),
    body: JSON.stringify(infraConfig),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<K8sManifest>;
}

export async function getDeploymentStatus(
  deploymentId: string,
  config: InfraClientConfig
): Promise<DeploymentStatus> {
  const res = await fetch(`${config.baseUrl}/infra/deployments/${deploymentId}`, {
    headers: headers(config.token),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<DeploymentStatus>;
}
