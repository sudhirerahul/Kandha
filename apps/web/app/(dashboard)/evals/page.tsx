// Evals Dashboard — LLM quality metrics and eval results
"use client";

import { useEffect, useState } from "react";
import { getLatestEvals, type EvalResults } from "@/lib/api";

export default function EvalsPage() {
  const [data, setData] = useState<EvalResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getLatestEvals()
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 max-w-5xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono mb-1">
          <span className="text-cyan-400">04</span>
          <span>/</span>
          <span>evals</span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">LLM Evaluations</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Quality metrics for Kimi K2 responses across cost analysis, migration safety, and security.
        </p>
      </div>

      {loading && (
        <div className="glass rounded-2xl p-10 text-center">
          <div className="flex flex-col items-center gap-4">
            <div className="relative w-12 h-12">
              <div className="absolute inset-0 rounded-full border-2 border-cyan-500/20" />
              <div className="absolute inset-0 rounded-full border-t-2 border-cyan-400 animate-spin" />
            </div>
            <div className="text-sm text-muted-foreground">Loading eval results...</div>
          </div>
        </div>
      )}

      {error && !loading && (
        <div className="glass rounded-2xl p-8 border border-red-400/20">
          <div className="text-sm font-semibold text-red-400 mb-1">Failed to load evals</div>
          <div className="text-xs text-muted-foreground">{error}</div>
        </div>
      )}

      {data && !loading && !data.summary && (
        <div className="glass rounded-2xl p-8 border border-border/50 text-center">
          <div className="text-sm text-muted-foreground mb-3">No eval results yet</div>
          <div className="text-xs text-muted-foreground font-mono">
            Run: <code className="text-cyan-400">cd apps/api && python -m evals.runner</code>
          </div>
        </div>
      )}

      {data?.summary && (
        <div className="space-y-6">
          {/* Summary cards */}
          <div className="grid grid-cols-4 gap-4">
            <MetricCard
              label="Pass Rate"
              value={`${Math.round(data.summary.pass_rate * 100)}%`}
              color={data.summary.pass_rate >= 0.8 ? "emerald" : data.summary.pass_rate >= 0.5 ? "amber" : "red"}
            />
            <MetricCard
              label="Avg Score"
              value={data.summary.avg_score.toFixed(3)}
              color={data.summary.avg_score >= 0.7 ? "emerald" : "amber"}
            />
            <MetricCard
              label="Avg Latency"
              value={`${Math.round(data.summary.avg_latency_ms)}ms`}
              color={data.summary.avg_latency_ms < 3000 ? "cyan" : "amber"}
            />
            <MetricCard
              label="Cases"
              value={`${data.summary.passed}/${data.summary.total}`}
              color="default"
              sub={`${data.summary.failed} failed`}
            />
          </div>

          {/* Per-category breakdown */}
          {data.by_category && (
            <div className="glass rounded-2xl p-6">
              <h2 className="text-sm font-semibold text-foreground mb-5">Results by Category</h2>
              <div className="space-y-4">
                {Object.entries(data.by_category).map(([category, cases]) => {
                  const passed = cases.filter((c) => c.passed).length;
                  const total = cases.length;
                  const pct = Math.round((passed / total) * 100);
                  return (
                    <div key={category}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-foreground">{formatCategory(category)}</span>
                        <span className={`text-xs font-mono ${pct === 100 ? "text-emerald-400" : pct >= 50 ? "text-amber-400" : "text-red-400"}`}>
                          {passed}/{total} passed
                        </span>
                      </div>
                      <div className="h-2 rounded-full overflow-hidden bg-card/60">
                        <div
                          className={`h-full rounded-full transition-all ${
                            pct === 100 ? "bg-emerald-400/60" : pct >= 50 ? "bg-amber-400/60" : "bg-red-400/60"
                          }`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      {/* Individual cases */}
                      <div className="mt-2 grid grid-cols-2 gap-2">
                        {cases.map((c) => (
                          <div
                            key={c.case_id}
                            className={`flex items-center justify-between px-3 py-2 rounded-lg border text-xs ${
                              c.passed
                                ? "border-emerald-400/10 bg-emerald-400/5"
                                : "border-red-400/10 bg-red-400/5"
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <span className={`w-1.5 h-1.5 rounded-full ${c.passed ? "bg-emerald-400" : "bg-red-400"}`} />
                              <span className="font-mono text-muted-foreground">{c.case_id}</span>
                            </div>
                            <div className="flex items-center gap-3">
                              <span className="text-muted-foreground">{c.overall_score.toFixed(2)}</span>
                              <span className="text-muted-foreground/50">{Math.round(c.latency_ms)}ms</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Score breakdown legend */}
          <div className="glass rounded-2xl p-6">
            <h2 className="text-sm font-semibold text-foreground mb-4">Scoring Rubric</h2>
            <div className="grid grid-cols-4 gap-4">
              <RubricItem name="Relevance" desc="Response addresses the prompt" />
              <RubricItem name="Specificity" desc="Concrete numbers, products, steps" />
              <RubricItem name="Safety" desc="No dangerous advice or data leaks" />
              <RubricItem name="Trait Match" desc="Expected terms present, forbidden absent" />
            </div>
          </div>

          {data.file && (
            <div className="text-xs text-muted-foreground/50 font-mono text-right">
              Source: {data.file}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Sub-components ───────────────────────────────────────────────────────────

function MetricCard({
  label,
  value,
  color,
  sub,
}: {
  label: string;
  value: string;
  color: "emerald" | "cyan" | "amber" | "red" | "default";
  sub?: string;
}) {
  const valueColor =
    color === "emerald" ? "text-emerald-400" :
    color === "cyan" ? "text-cyan-400" :
    color === "amber" ? "text-amber-400" :
    color === "red" ? "text-red-400" :
    "text-foreground";

  return (
    <div className="glass rounded-2xl p-5">
      <div className="text-xs text-muted-foreground mb-2">{label}</div>
      <div className={`text-2xl font-bold font-mono ${valueColor}`}>{value}</div>
      {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
    </div>
  );
}

function RubricItem({ name, desc }: { name: string; desc: string }) {
  return (
    <div className="p-3 rounded-lg border border-border/40">
      <div className="text-xs font-semibold text-foreground mb-1">{name}</div>
      <div className="text-xs text-muted-foreground">{desc}</div>
    </div>
  );
}

function formatCategory(cat: string): string {
  return cat.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
