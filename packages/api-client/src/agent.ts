// agent.ts — Typed client for /agent endpoints (repatriation agent sessions)
import type { AgentSession, MigrationPlan } from "@kandha/types";

export interface AgentClientConfig {
  baseUrl: string;
  token?: string;
}

function headers(token?: string): HeadersInit {
  const h: HeadersInit = { "Content-Type": "application/json" };
  if (token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

export async function createSession(
  reportId: string,
  config: AgentClientConfig
): Promise<AgentSession> {
  const res = await fetch(`${config.baseUrl}/agent/sessions`, {
    method: "POST",
    headers: headers(config.token),
    body: JSON.stringify({ report_id: reportId }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<AgentSession>;
}

export async function getMigrationPlan(
  sessionId: string,
  config: AgentClientConfig
): Promise<MigrationPlan> {
  const res = await fetch(`${config.baseUrl}/agent/sessions/${sessionId}/plan`, {
    headers: headers(config.token),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<MigrationPlan>;
}

/**
 * Returns a ReadableStream of SSE chunks from the agent.
 * Caller is responsible for consuming the stream.
 */
export function streamAgentMessage(
  sessionId: string,
  message: string,
  config: AgentClientConfig
): Promise<Response> {
  return fetch(`${config.baseUrl}/agent/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: headers(config.token),
    body: JSON.stringify({ content: message }),
  });
}
