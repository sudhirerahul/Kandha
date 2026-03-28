// analyze.ts — Typed client for /analyze endpoints (cloud bill parsing & savings reports)
import type { AnalysisReport, BillUploadResponse, SavingsEstimate } from "@kandha/types";

export interface ApiClientConfig {
  baseUrl: string;
  token?: string;
}

function headers(token?: string): HeadersInit {
  const h: HeadersInit = { "Content-Type": "application/json" };
  if (token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

export async function uploadBill(
  file: File,
  config: ApiClientConfig
): Promise<BillUploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${config.baseUrl}/analyze/upload`, {
    method: "POST",
    headers: config.token ? { Authorization: `Bearer ${config.token}` } : {},
    body: form,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<BillUploadResponse>;
}

export async function getAnalysisReport(
  reportId: string,
  config: ApiClientConfig
): Promise<AnalysisReport> {
  const res = await fetch(`${config.baseUrl}/analyze/reports/${reportId}`, {
    headers: headers(config.token),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<AnalysisReport>;
}

export async function getSavingsEstimate(
  reportId: string,
  config: ApiClientConfig
): Promise<SavingsEstimate> {
  const res = await fetch(`${config.baseUrl}/analyze/reports/${reportId}/savings`, {
    headers: headers(config.token),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<SavingsEstimate>;
}
