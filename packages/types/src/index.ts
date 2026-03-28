// Shared TypeScript types for the Kandha platform

// ---------------------------------------------------------------------------
// Cost Analyzer
// ---------------------------------------------------------------------------

export interface SpendBreakdown {
  compute_usd: number;
  storage_usd: number;
  egress_usd: number;
  database_usd: number;
  support_usd: number;
  other_usd: number;
}

export interface HardwareRecommendation {
  provider: "hetzner" | "ovh" | "onprem";
  tier: string; // e.g. "cx41", "rise-3"
  vcpu: number;
  ram_gb: number;
  storage_gb: number;
  monthly_cost_usd: number;
  annual_saving_usd: number;
  justification: string;
}

export interface SpendReport {
  id: string;
  session_id: string;
  total_monthly_usd: number;
  breakdown: SpendBreakdown;
  savings_report: {
    summary: string;
    projected_monthly_saving_usd: number;
    projected_annual_saving_usd: number;
    confidence: "high" | "medium" | "low";
    key_findings: string[];
  };
  hardware_recommendations: HardwareRecommendation[];
  created_at: string;
}

export interface AnalysisSession {
  id: string;
  user_id: string;
  status: "pending" | "processing" | "complete" | "error";
  file_name: string;
  created_at: string;
  spend_report?: SpendReport;
}

// ---------------------------------------------------------------------------
// Repatriation Agent
// ---------------------------------------------------------------------------

export interface AgentTurn {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface AgentSession {
  id: string;
  user_id: string;
  analysis_session_id?: string;
  hydra_session_id: string;
  status: "active" | "archived";
  title?: string;
  created_at: string;
  updated_at: string;
  turns?: AgentTurn[];
}

// ---------------------------------------------------------------------------
// Infra Configurator
// ---------------------------------------------------------------------------

export type WorkloadProfile =
  | "web"
  | "ml"
  | "database_heavy"
  | "mixed"
  | "high_availability";

export type ClusterType = "k3s" | "k8s";

export interface InfraConfig {
  id: string;
  provider: "hetzner" | "ovh" | "onprem";
  region: string;
  server_type: string;
  node_count: number;
  cluster_type: ClusterType;
  workload_profile: WorkloadProfile;
  addons: string[]; // e.g. ["prometheus", "grafana", "argocd", "minio"]
  manifests?: GeneratedManifests;
}

export interface GeneratedManifests {
  deployment_yaml: string;
  service_yaml: string;
  ingress_yaml: string;
  helm_values_yaml: string;
  setup_script: string;
}
