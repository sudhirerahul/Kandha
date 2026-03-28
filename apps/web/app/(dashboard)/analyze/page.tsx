// Cost Analyzer — real file upload → FastAPI → GMI savings report
"use client";

import { useRef, useState } from "react";
import { useUser } from "@clerk/nextjs";
import {
  uploadBill,
  type AnalysisResult,
  type HardwareRecommendation,
  type ServiceBreakdown,
} from "@/lib/api";

type State = "idle" | "uploading" | "done" | "error";

export default function AnalyzePage() {
  const { user } = useUser();
  const userId = user?.id ?? "anonymous";

  const [state, setState] = useState<State>("idle");
  const [dragOver, setDragOver] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    setFileName(file.name);
    setState("uploading");
    setErrorMsg(null);
    try {
      const data = await uploadBill(file, userId);
      setResult(data);
      setState("done");
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "Upload failed");
      setState("error");
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) void handleFile(file);
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) void handleFile(file);
  }

  function reset() {
    setState("idle");
    setResult(null);
    setFileName(null);
    setErrorMsg(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <div className="p-8 max-w-5xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono mb-1">
          <span className="text-cyan-400">01</span>
          <span>/</span>
          <span>cost-analyzer</span>
          {result && (
            <>
              <span className="text-muted-foreground/40">·</span>
              <span className="text-emerald-400">{result.provider.toUpperCase()}</span>
            </>
          )}
        </div>
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Cost Analyzer</h1>
          {state === "done" && (
            <button
              onClick={reset}
              className="text-xs text-muted-foreground border border-border/50 rounded-lg px-3 py-1.5 hover:border-border hover:text-foreground transition-colors cursor-pointer"
            >
              Upload another
            </button>
          )}
        </div>
        <p className="text-sm text-muted-foreground mt-1">
          Upload your cloud bill — get an instant savings report powered by Kimi K2.
        </p>
      </div>

      {state === "idle" && (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`relative rounded-2xl border-2 border-dashed p-16 text-center cursor-pointer transition-all duration-200 ${
            dragOver
              ? "border-cyan-400/60 bg-cyan-500/5 shadow-[0_0_30px_hsl(189_100%_53%/0.1)]"
              : "border-border/50 hover:border-cyan-400/30 hover:bg-card/30"
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".csv,.json"
            className="hidden"
            onChange={handleChange}
          />
          <div className="flex flex-col items-center gap-4">
            <div className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-colors ${dragOver ? "bg-cyan-500/20" : "bg-card/60 border border-border/50"}`}>
              <UploadIcon className={`w-6 h-6 ${dragOver ? "text-cyan-400" : "text-muted-foreground"}`} />
            </div>
            <div>
              <div className="text-sm font-semibold text-foreground mb-1">Drop your cloud bill here</div>
              <div className="text-xs text-muted-foreground">AWS Cost Explorer CSV · GCP Billing CSV · Azure Cost Management</div>
            </div>
            <span className="text-xs font-medium text-cyan-400 border border-cyan-500/20 rounded-lg px-3 py-1.5 bg-cyan-500/5">
              Browse files
            </span>
          </div>
        </div>
      )}

      {state === "uploading" && (
        <div className="glass rounded-2xl p-10 text-center">
          <div className="flex flex-col items-center gap-5">
            <div className="relative w-14 h-14">
              <div className="absolute inset-0 rounded-full border-2 border-cyan-500/20" />
              <div className="absolute inset-0 rounded-full border-t-2 border-cyan-400 animate-spin" />
            </div>
            <div>
              <div className="text-sm font-semibold text-foreground mb-1">Analysing {fileName}…</div>
              <div className="text-xs text-muted-foreground font-mono">
                Parsing line items · querying pricing · running Kimi K2 analysis
              </div>
            </div>
          </div>
        </div>
      )}

      {state === "error" && (
        <div className="glass rounded-2xl p-8 border border-red-400/20">
          <div className="text-sm font-semibold text-red-400 mb-1">Analysis failed</div>
          <div className="text-xs text-muted-foreground mb-4">{errorMsg}</div>
          <button
            onClick={reset}
            className="text-xs font-medium bg-red-400/10 text-red-400 border border-red-400/20 rounded-lg px-4 py-2 hover:bg-red-400/15 transition-colors cursor-pointer"
          >
            Try again
          </button>
        </div>
      )}

      {state === "done" && result && <AnalysisResults result={result} />}
    </div>
  );
}

// ─── Results panel ────────────────────────────────────────────────────────────

function AnalysisResults({ result }: { result: AnalysisResult }) {
  const topRec = result.hardware_recommendations[0];
  const savingsPct = topRec
    ? Math.round(topRec.savings_pct)
    : 0;

  return (
    <div className="space-y-5">
      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4">
        <SummaryCard
          label="Current monthly spend"
          value={`$${result.total_usd.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
          sub={`${result.provider.toUpperCase()} · ${result.line_items.toLocaleString()} line items`}
          color="default"
        />
        {topRec ? (
          <SummaryCard
            label="Projected bare-metal cost"
            value={`$${topRec.price_mo.toLocaleString()}/mo`}
            sub={`${topRec.model} × ${topRec.nodes} nodes · Hetzner`}
            color="cyan"
          />
        ) : (
          <SummaryCard label="Projected cost" value="—" sub="No recommendation available" color="default" />
        )}
        {topRec ? (
          <SummaryCard
            label="Monthly savings"
            value={`$${topRec.savings_mo.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
            sub={`${savingsPct}% reduction · $${(topRec.savings_mo * 12 / 1000).toFixed(0)}k/year`}
            color="emerald"
            highlight
          />
        ) : (
          <SummaryCard label="Savings" value="—" sub="Upload a larger bill to see recommendations" color="default" />
        )}
      </div>

      {/* AI Summary */}
      {result.savings_report.summary && (
        <div className="glass rounded-2xl p-5 border border-cyan-500/10">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
            <span className="text-xs font-semibold text-cyan-400">Kimi K2 Analysis</span>
            <span className="text-xs text-muted-foreground/50 font-mono ml-auto">
              via {result.savings_report.source === "dify" ? "Dify workflow" : "GMI direct"}
            </span>
          </div>
          <p className="text-sm text-foreground/80 leading-relaxed">{result.savings_report.summary}</p>
        </div>
      )}

      {/* Service breakdown */}
      <div className="glass rounded-2xl p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-sm font-semibold text-foreground">Service breakdown</h2>
          <span className="text-xs text-muted-foreground font-mono">{result.provider.toUpperCase()}</span>
        </div>
        <div className="space-y-3">
          {result.breakdown.slice(0, 10).map((svc: ServiceBreakdown) => {
            const pct = Math.round((svc.cost_usd / result.total_usd) * 100);
            return (
              <div key={svc.service}>
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="text-foreground/80 font-medium truncate max-w-[50%]">{svc.service}</span>
                  <span className="text-muted-foreground font-mono">
                    ${svc.cost_usd.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                    <span className="text-muted-foreground/50 ml-2">{pct}%</span>
                  </span>
                </div>
                <div className="h-1.5 rounded-full overflow-hidden bg-card/60">
                  <div
                    className="h-full bg-cyan-400/60 rounded-full transition-all"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Hardware recommendations */}
      {result.hardware_recommendations.length > 0 && (
        <div className="glass rounded-2xl p-6">
          <h2 className="text-sm font-semibold text-foreground mb-4">Hardware recommendations</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {result.hardware_recommendations.map((rec: HardwareRecommendation, i: number) => (
              <div
                key={i}
                className={`rounded-xl border p-4 ${i === 0 ? "border-cyan-400/25 bg-cyan-500/5" : "border-border/40"}`}
              >
                <div className="text-sm font-bold font-mono text-cyan-400 mb-1">
                  {rec.model} × {rec.nodes}
                </div>
                <div className="text-xs text-muted-foreground mb-2">
                  {rec.vcpu_total} vCPU · {rec.ram_gb_total}GB RAM
                </div>
                <div className="text-xs font-mono text-foreground">${rec.price_mo}/mo</div>
                <div className="text-xs text-emerald-400 mt-0.5">-{rec.savings_pct}% savings</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* CTA */}
      <div className="grid grid-cols-2 gap-4">
        <a
          href="/agent"
          className="flex items-center justify-center gap-2 bg-cyan-500 text-background rounded-xl py-3 text-sm font-semibold hover:bg-cyan-400 transition-all cursor-pointer hover:shadow-[0_0_20px_hsl(189_100%_53%/0.3)]"
        >
          Start migration plan
          <ArrowRightIcon />
        </a>
        <button className="border border-border/50 text-muted-foreground rounded-xl py-3 text-xs font-medium hover:border-border hover:text-foreground transition-colors cursor-pointer">
          Export PDF report
        </button>
      </div>
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SummaryCard({
  label, value, sub, color, highlight,
}: {
  label: string; value: string; sub: string; color: "default" | "cyan" | "emerald"; highlight?: boolean;
}) {
  const valueColor = color === "cyan" ? "text-cyan-400" : color === "emerald" ? "text-emerald-400" : "text-foreground";
  return (
    <div className={`glass rounded-2xl p-5 ${highlight ? "border border-emerald-400/15 shadow-[0_0_20px_hsl(158_64%_52%/0.05)]" : ""}`}>
      <div className="text-xs text-muted-foreground mb-2">{label}</div>
      <div className={`text-2xl font-bold font-mono ${valueColor}`}>{value}</div>
      <div className="text-xs text-muted-foreground mt-1.5">{sub}</div>
    </div>
  );
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function UploadIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

function ArrowRightIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14M12 5l7 7-7 7" />
    </svg>
  );
}
