// Infra Configurator — 3-step wizard: provider -> workload -> real K8s manifests from API
"use client";

import { useState } from "react";
import { generateInfra, type InfraResult, type ManifestItem } from "@/lib/api";

type Step = 1 | 2 | 3;

const PROVIDERS = [
  { id: "hetzner", name: "Hetzner Cloud", region: "Falkenstein / Nuremberg / Helsinki", price: "From $36/mo" },
  { id: "ovh", name: "OVH Bare Metal", region: "Paris / Frankfurt / London", price: "From $44/mo" },
  { id: "on-prem", name: "On-Premises", region: "Your data center", price: "Hardware only" },
];

const WORKLOADS = [
  { id: "web", name: "Web / API", desc: "Next.js, FastAPI, Node.js — low memory, high concurrency" },
  { id: "ml", name: "ML / GPU", desc: "Model inference, training — GPU-optimized instances" },
  { id: "database_heavy", name: "Database-heavy", desc: "PostgreSQL, Redis, Elasticsearch — high IOPS NVMe" },
  { id: "mixed", name: "Mixed / General", desc: "Balanced CPU + RAM for multi-service workloads" },
];

const SIZES = [
  { id: "small", name: "Small", spec: "8 vCPU / 32GB RAM / 512GB NVMe", price: "$49/mo", nodes: 1 },
  { id: "medium", name: "Medium", spec: "32 vCPU / 64GB RAM / 1.9TB NVMe", price: "$89/mo", nodes: 3 },
  { id: "large", name: "Large", spec: "96 vCPU / 192GB RAM / 3.8TB NVMe", price: "$136/mo", nodes: 3 },
];

export default function ConfigurePage() {
  const [step, setStep] = useState<Step>(1);
  const [provider, setProvider] = useState("hetzner");
  const [workload, setWorkload] = useState("web");
  const [size, setSize] = useState("medium");
  const [appName, setAppName] = useState("my-app");

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<InfraResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  const [copied, setCopied] = useState(false);

  async function handleGenerate() {
    setStep(3);
    setLoading(true);
    setError(null);
    try {
      const data = await generateInfra({ provider, workload, size, app_name: appName });
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  }

  function copyManifest(text: string) {
    navigator.clipboard.writeText(text).catch(() => undefined);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function downloadZip() {
    if (!result) return;
    // Build a combined YAML string and download as .yaml
    const combined = result.manifests.map((m) => m.yaml).join("\n---\n");
    const blob = new Blob([combined], { type: "text/yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${appName}-k8s-manifests.yaml`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const activeManifest = result?.manifests[activeTab];

  return (
    <div className="p-8 max-w-4xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono mb-1">
          <span className="text-cyan-400">03</span>
          <span>/</span>
          <span>infra-configurator</span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Infra Configurator</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Configure your target cluster and generate production-ready Kubernetes manifests.
        </p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-0 mb-8">
        {([1, 2, 3] as Step[]).map((s) => (
          <div key={s} className="flex items-center">
            <button
              onClick={() => s < step ? setStep(s) : undefined}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-default ${
                step === s
                  ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                  : s < step
                  ? "text-muted-foreground hover:text-foreground cursor-pointer"
                  : "text-muted-foreground/40"
              }`}
            >
              <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-mono border ${
                step === s ? "border-cyan-500/40 bg-cyan-500/10 text-cyan-400" :
                s < step ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-400" :
                "border-border/40 text-muted-foreground/40"
              }`}>
                {s < step ? "\u2713" : s}
              </span>
              {s === 1 ? "Provider" : s === 2 ? "Workload" : "Generate"}
            </button>
            {s < 3 && <div className={`w-8 h-px mx-1 ${s < step ? "bg-emerald-400/30" : "bg-border/40"}`} />}
          </div>
        ))}
      </div>

      {/* Step 1: Provider */}
      {step === 1 && (
        <div className="space-y-6">
          <div>
            <h2 className="text-sm font-semibold text-foreground mb-4">Choose your target provider</h2>
            <div className="grid gap-3">
              {PROVIDERS.map((p) => (
                <button
                  key={p.id}
                  onClick={() => setProvider(p.id)}
                  className={`flex items-center justify-between p-4 rounded-xl border text-left transition-all cursor-pointer ${
                    provider === p.id
                      ? "border-cyan-400/30 bg-cyan-500/5 shadow-[0_0_16px_hsl(189_100%_53%/0.06)]"
                      : "border-border/50 hover:border-border glass/30 hover:bg-card/40"
                  }`}
                >
                  <div>
                    <div className="text-sm font-semibold text-foreground">{p.name}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{p.region}</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-mono text-cyan-400">{p.price}</span>
                    <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                      provider === p.id ? "border-cyan-400" : "border-border"
                    }`}>
                      {provider === p.id && <div className="w-2 h-2 rounded-full bg-cyan-400" />}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div>
            <h2 className="text-sm font-semibold text-foreground mb-4">Node size</h2>
            <div className="grid grid-cols-3 gap-3">
              {SIZES.map((s) => (
                <button
                  key={s.id}
                  onClick={() => setSize(s.id)}
                  className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
                    size === s.id
                      ? "border-cyan-400/30 bg-cyan-500/5"
                      : "border-border/50 hover:border-border glass/30"
                  }`}
                >
                  <div className="text-sm font-semibold text-foreground mb-1">{s.name}</div>
                  <div className="text-xs text-muted-foreground leading-relaxed">{s.spec}</div>
                  <div className="text-xs font-mono text-cyan-400 mt-2">{s.price} x {s.nodes} nodes</div>
                </button>
              ))}
            </div>
          </div>

          <div>
            <h2 className="text-sm font-semibold text-foreground mb-2">App name</h2>
            <input
              type="text"
              value={appName}
              onChange={(e) => setAppName(e.target.value.replace(/[^a-z0-9-]/g, ""))}
              className="bg-card/40 border border-border/50 rounded-lg px-3 py-2 text-sm text-foreground font-mono w-64 focus:outline-none focus:border-cyan-400/30"
              placeholder="my-app"
            />
          </div>

          <button
            onClick={() => setStep(2)}
            className="flex items-center gap-2 bg-cyan-500 text-background rounded-xl px-6 py-3 text-sm font-semibold hover:bg-cyan-400 transition-all cursor-pointer hover:shadow-[0_0_20px_hsl(189_100%_53%/0.3)]"
          >
            Continue
            <ArrowRightIcon />
          </button>
        </div>
      )}

      {/* Step 2: Workload */}
      {step === 2 && (
        <div className="space-y-6">
          <div>
            <h2 className="text-sm font-semibold text-foreground mb-4">What type of workload are you running?</h2>
            <div className="grid grid-cols-2 gap-3">
              {WORKLOADS.map((w) => (
                <button
                  key={w.id}
                  onClick={() => setWorkload(w.id)}
                  className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
                    workload === w.id
                      ? "border-cyan-400/30 bg-cyan-500/5 shadow-[0_0_16px_hsl(189_100%_53%/0.06)]"
                      : "border-border/50 hover:border-border glass/30"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="text-sm font-semibold text-foreground mb-1">{w.name}</div>
                      <div className="text-xs text-muted-foreground leading-relaxed">{w.desc}</div>
                    </div>
                    <div className={`w-4 h-4 rounded-full border-2 mt-0.5 shrink-0 flex items-center justify-center ${
                      workload === w.id ? "border-cyan-400" : "border-border"
                    }`}>
                      {workload === w.id && <div className="w-2 h-2 rounded-full bg-cyan-400" />}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setStep(1)}
              className="border border-border/50 text-muted-foreground rounded-xl px-5 py-3 text-sm font-medium hover:border-border hover:text-foreground transition-colors cursor-pointer"
            >
              Back
            </button>
            <button
              onClick={handleGenerate}
              className="flex items-center gap-2 bg-cyan-500 text-background rounded-xl px-6 py-3 text-sm font-semibold hover:bg-cyan-400 transition-all cursor-pointer hover:shadow-[0_0_20px_hsl(189_100%_53%/0.3)]"
            >
              Generate manifests
              <ArrowRightIcon />
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Generated output */}
      {step === 3 && (
        <div className="space-y-5">
          {/* Summary badges */}
          <div className="flex items-center gap-3 flex-wrap">
            <ConfigBadge label="Provider" value={PROVIDERS.find((p) => p.id === provider)?.name ?? provider} />
            <ConfigBadge label="Workload" value={WORKLOADS.find((w) => w.id === workload)?.name ?? workload} />
            <ConfigBadge label="Size" value={SIZES.find((s) => s.id === size)?.name ?? size} />
            <ConfigBadge label="App" value={appName} />
            <button
              onClick={() => { setStep(1); setResult(null); }}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer ml-auto"
            >
              Edit config
            </button>
          </div>

          {/* Loading state */}
          {loading && (
            <div className="glass rounded-2xl p-10 text-center">
              <div className="flex flex-col items-center gap-5">
                <div className="relative w-14 h-14">
                  <div className="absolute inset-0 rounded-full border-2 border-cyan-500/20" />
                  <div className="absolute inset-0 rounded-full border-t-2 border-cyan-400 animate-spin" />
                </div>
                <div>
                  <div className="text-sm font-semibold text-foreground mb-1">Generating K8s manifests...</div>
                  <div className="text-xs text-muted-foreground font-mono">
                    Rendering templates / Running Kimi K2 review / Building setup script
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Error state */}
          {error && !loading && (
            <div className="glass rounded-2xl p-8 border border-red-400/20">
              <div className="text-sm font-semibold text-red-400 mb-1">Generation failed</div>
              <div className="text-xs text-muted-foreground mb-4">{error}</div>
              <button
                onClick={handleGenerate}
                className="text-xs font-medium bg-red-400/10 text-red-400 border border-red-400/20 rounded-lg px-4 py-2 hover:bg-red-400/15 transition-colors cursor-pointer"
              >
                Try again
              </button>
            </div>
          )}

          {/* Results */}
          {result && !loading && (
            <>
              {/* AI review */}
              {result.ai_customizations && (
                <div className="glass rounded-2xl p-5 border border-cyan-500/10">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                    <span className="text-xs font-semibold text-cyan-400">Kimi K2 Review</span>
                  </div>
                  <p className="text-sm text-foreground/80 leading-relaxed">{result.ai_customizations}</p>
                </div>
              )}

              {/* Manifest tabs */}
              <div className="glass rounded-2xl overflow-hidden border border-border/60">
                <div className="flex items-center gap-0 px-3 pt-2 border-b border-border/40 bg-card/30 overflow-x-auto">
                  {result.manifests.map((m: ManifestItem, i: number) => (
                    <button
                      key={i}
                      onClick={() => setActiveTab(i)}
                      className={`px-3 py-2 text-xs font-mono transition-colors cursor-pointer border-b-2 -mb-px ${
                        activeTab === i
                          ? "text-cyan-400 border-cyan-400"
                          : "text-muted-foreground border-transparent hover:text-foreground"
                      }`}
                    >
                      {m.kind}
                    </button>
                  ))}
                </div>
                <div className="flex items-center justify-between px-5 py-2 border-b border-border/40 bg-card/20">
                  <span className="text-xs font-mono text-muted-foreground">
                    {activeManifest?.name}.yaml
                  </span>
                  <button
                    onClick={() => activeManifest && copyManifest(activeManifest.yaml)}
                    className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground border border-border/40 rounded-md px-2.5 py-1 hover:border-border transition-colors cursor-pointer"
                  >
                    {copied ? <CheckIcon /> : <CopyIcon />}
                    {copied ? "Copied!" : "Copy"}
                  </button>
                </div>
                <pre className="p-5 text-xs font-mono text-muted-foreground leading-relaxed overflow-x-auto max-h-[380px] overflow-y-auto whitespace-pre">
                  <code>
                    {activeManifest?.yaml.split("\n").map((line: string, i: number) => (
                      <span key={i} className={`block ${
                        line.startsWith("#") ? "text-muted-foreground/50" :
                        line.startsWith("apiVersion") || line.startsWith("kind") ? "text-cyan-400/80" :
                        line.includes(":") && !line.startsWith(" ") ? "text-foreground/90" :
                        "text-muted-foreground/70"
                      }`}>
                        {line}
                      </span>
                    ))}
                  </code>
                </pre>
              </div>

              {/* Deploy actions */}
              <div className="grid grid-cols-3 gap-3">
                <button
                  onClick={() => {
                    const all = result.manifests.map((m) => m.yaml).join("\n---\n");
                    copyManifest(all);
                  }}
                  className="flex items-center justify-center gap-2 bg-cyan-500 text-background rounded-xl py-3 text-sm font-semibold hover:bg-cyan-400 transition-all cursor-pointer hover:shadow-[0_0_20px_hsl(189_100%_53%/0.3)]"
                >
                  <CopyIcon />
                  Copy all manifests
                </button>
                <button
                  onClick={downloadZip}
                  className="flex items-center justify-center gap-2 border border-border/50 text-muted-foreground rounded-xl py-3 text-sm font-medium hover:border-border hover:text-foreground transition-colors cursor-pointer"
                >
                  <DownloadIcon />
                  Download .yaml
                </button>
                <button className="flex items-center justify-center gap-2 border border-border/50 text-muted-foreground rounded-xl py-3 text-sm font-medium hover:border-border hover:text-foreground transition-colors cursor-pointer">
                  <DeployIcon />
                  One-click deploy
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ── Sub-components ───────────────────────────────────────────────────────────

function ConfigBadge({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-1.5 border border-border/50 rounded-lg px-3 py-1.5">
      <span className="text-xs text-muted-foreground">{label}:</span>
      <span className="text-xs font-medium text-foreground">{value}</span>
    </div>
  );
}

// ── Icons ────────────────────────────────────────────────────────────────────

function ArrowRightIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14M12 5l7 7-7 7" />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}

function DeployIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="5 3 19 12 5 21 5 3" />
    </svg>
  );
}
