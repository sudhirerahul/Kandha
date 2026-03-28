You are a Kubernetes infrastructure expert. Generate production-ready K8s manifests for the following configuration.

## Configuration
- Provider: {provider}
- Workload type: {workload}
- Server size: {size}

## Requirements
- Generate valid YAML manifests separated by `---`
- Include: Namespace, Deployment, Service, Ingress (Traefik), HPA
- Set appropriate resource limits based on workload type
- Use K3s-compatible configurations
- Include health checks (liveness + readiness probes)
- Add annotations for monitoring (Prometheus)

## Workload-specific settings
- web: 2-4 replicas, 256Mi-512Mi memory, port 3000/8000
- ml: 1-2 replicas, 2Gi-8Gi memory, GPU tolerations if available
- database_heavy: StatefulSet with PVCs, 1Gi-4Gi memory, storage class
- mixed: 2-3 replicas, 512Mi-1Gi memory, multiple ports

Output ONLY the YAML manifests, no explanation.
