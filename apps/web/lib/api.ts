// lib/api.ts — typed fetch helpers for the Kandha FastAPI backend
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ServiceBreakdown {
  service: string;
  cost_usd: number;
  usage: number;
  region: string;
}

export interface HardwareRecommendation {
  provider: string;
  model: string;
  nodes: number;
  vcpu_total: number;
  ram_gb_total: number;
  price_mo: number;
  savings_mo: number;
  savings_pct: number;
}

export interface AnalysisResult {
  analysis_session_id: string;
  status: string;
  provider: string;
  line_items: number;
  total_usd: number;
  breakdown: ServiceBreakdown[];
  savings_report: { summary?: string; source?: string; [key: string]: unknown };
  hardware_recommendations: HardwareRecommendation[];
}

export interface AgentSession {
  session_id: string;
  hydra_session_id: string;
}

export interface SSEChunk {
  type: "chunk" | "done" | "error";
  content?: string;
  session_id?: string;
  message?: string;
}

// ── Infra types ─────────────────────────────────────────────────────────────

export interface ManifestItem {
  kind: string;
  name: string;
  yaml: string;
}

export interface InfraResult {
  manifests: ManifestItem[];
  helm_values: Record<string, unknown>;
  setup_script: string;
  provider: string;
  workload: string;
  ai_customizations: string | null;
}

export interface InfraValidation {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface TemplatePreset {
  name: string;
  description: string;
  workload: string;
  replicas: number;
  memory: string;
}

// ── Eval types ──────────────────────────────────────────────────────────────

export interface EvalSummary {
  total: number;
  passed: number;
  failed: number;
  pass_rate: number;
  avg_score: number;
  avg_latency_ms: number;
}

export interface EvalResults {
  summary: EvalSummary | null;
  by_category?: Record<string, Array<{
    case_id: string;
    passed: boolean;
    overall_score: number;
    scores: Record<string, number>;
    latency_ms: number;
  }>>;
  file?: string;
  message?: string;
}

// ── Auth helper ─────────────────────────────────────────────────────────────

let _getToken: (() => Promise<string | null>) | null = null;

export function setAuthTokenProvider(fn: () => Promise<string | null>) {
  _getToken = fn;
}

async function authHeaders(extra?: Record<string, string>): Promise<Record<string, string>> {
  const headers: Record<string, string> = { ...extra };
  if (_getToken) {
    const token = await _getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }
  return headers;
}

// ── Retry helper ────────────────────────────────────────────────────────────

async function fetchWithRetry(
  url: string,
  init: RequestInit,
  maxRetries = 2,
): Promise<Response> {
  let lastError: Error | null = null;
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const res = await fetch(url, init);
    if (res.status !== 429) return res;

    // Rate limited — exponential backoff
    const retryAfter = parseInt(res.headers.get("Retry-After") ?? "2", 10);
    const delay = Math.min(retryAfter * 1000 * (attempt + 1), 10000);
    lastError = new Error(`Rate limited (429). Retry after ${retryAfter}s`);
    if (attempt < maxRetries) {
      await new Promise((r) => setTimeout(r, delay));
    }
  }
  throw lastError ?? new Error("Rate limited");
}

// ── Analyze ─────────────────────────────────────────────────────────────────

export async function uploadBill(
  file: File,
  userId: string,
): Promise<AnalysisResult> {
  const form = new FormData();
  form.append("file", file);

  const headers = await authHeaders({ "X-User-Id": userId });
  const res = await fetchWithRetry(`${BASE}/api/v1/analyze/upload`, {
    method: "POST",
    headers,
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Upload failed");
  }

  return res.json() as Promise<AnalysisResult>;
}

// ── Agent ───────────────────────────────────────────────────────────────────

export async function createAgentSession(
  userId: string,
  analysisSessionId?: string,
): Promise<AgentSession> {
  const headers = await authHeaders({
    "Content-Type": "application/json",
    "X-User-Id": userId,
  });
  const res = await fetchWithRetry(`${BASE}/api/v1/agent/sessions`, {
    method: "POST",
    headers,
    body: JSON.stringify({ analysis_session_id: analysisSessionId ?? null }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Failed to create session");
  }

  return res.json() as Promise<AgentSession>;
}

export async function sendAgentMessage(
  sessionId: string,
  content: string,
  userId: string,
): Promise<ReadableStream<SSEChunk>> {
  const headers = await authHeaders({
    "Content-Type": "application/json",
    "X-User-Id": userId,
  });
  const res = await fetch(
    `${BASE}/api/v1/agent/sessions/${sessionId}/messages`,
    { method: "POST", headers, body: JSON.stringify({ content }) },
  );

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Failed to send message");
  }

  const body = res.body!;
  const decoder = new TextDecoder();
  let buffer = "";

  return new ReadableStream<SSEChunk>({
    async pull(controller) {
      const reader = body.getReader();
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          controller.close();
          return;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const chunk = JSON.parse(line.slice(6)) as SSEChunk;
            controller.enqueue(chunk);
            if (chunk.type === "done" || chunk.type === "error") {
              controller.close();
              return;
            }
          } catch {
            // malformed SSE line — skip
          }
        }
      }
    },
  });
}

// ── Infra ───────────────────────────────────────────────────────────────────

export async function generateInfra(config: {
  provider: string;
  workload: string;
  size: string;
  app_name?: string;
  domain?: string;
}): Promise<InfraResult> {
  const headers = await authHeaders({ "Content-Type": "application/json" });
  const res = await fetchWithRetry(`${BASE}/api/v1/infra/generate`, {
    method: "POST",
    headers,
    body: JSON.stringify(config),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Failed to generate infrastructure");
  }

  return res.json() as Promise<InfraResult>;
}

export async function getTemplates(): Promise<TemplatePreset[]> {
  const headers = await authHeaders();
  const res = await fetch(`${BASE}/api/v1/infra/templates`, { headers });
  if (!res.ok) throw new Error("Failed to fetch templates");
  return res.json() as Promise<TemplatePreset[]>;
}

export async function validateInfra(yaml: string): Promise<InfraValidation> {
  const headers = await authHeaders({ "Content-Type": "application/json" });
  const res = await fetch(`${BASE}/api/v1/infra/validate`, {
    method: "POST",
    headers,
    body: JSON.stringify({ yaml_content: yaml }),
  });
  if (!res.ok) throw new Error("Validation failed");
  return res.json() as Promise<InfraValidation>;
}

// ── Evals ───────────────────────────────────────────────────────────────────

export async function getLatestEvals(): Promise<EvalResults> {
  const headers = await authHeaders();
  const res = await fetch(`${BASE}/api/v1/evals/latest`, { headers });
  if (!res.ok) throw new Error("Failed to fetch eval results");
  return res.json() as Promise<EvalResults>;
}

export async function getEvalHistory(): Promise<{ runs: Array<{ file: string; timestamp: string; summary: EvalSummary }> }> {
  const headers = await authHeaders();
  const res = await fetch(`${BASE}/api/v1/evals/history`, { headers });
  if (!res.ok) throw new Error("Failed to fetch eval history");
  return res.json();
}
