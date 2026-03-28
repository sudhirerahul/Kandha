// Landing page — animated hero, feature cards, stats, CTA
import Link from "next/link";
import { SignInButton, SignedIn, SignedOut } from "@clerk/nextjs";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background bg-dot-grid relative overflow-hidden">
      {/* Ambient glow orbs */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-cyan-500/5 blur-[120px]" />
        <div className="absolute top-1/2 -right-40 w-[400px] h-[400px] rounded-full bg-emerald-400/4 blur-[100px]" />
      </div>

      {/* Floating Nav */}
      <header className="fixed top-4 left-0 right-0 z-50 px-4">
        <nav className="max-w-5xl mx-auto glass rounded-xl px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <KandhaLogo />
            <span className="text-sm font-semibold tracking-tight text-foreground">Kandha</span>
          </div>
          <div className="hidden md:flex items-center gap-6">
            <a href="#features" className="text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
              Features
            </a>
            <a href="#how" className="text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
              How it works
            </a>
            <a href="#pricing" className="text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
              Pricing
            </a>
          </div>
          <div className="flex items-center gap-2">
            <SignedOut>
              <SignInButton mode="modal">
                <button className="text-xs font-medium text-muted-foreground hover:text-foreground transition-colors cursor-pointer px-3 py-1.5">
                  Sign in
                </button>
              </SignInButton>
              <Link
                href="/sign-up"
                className="text-xs font-semibold bg-cyan-500 text-background rounded-lg px-4 py-2 hover:bg-cyan-400 transition-colors cursor-pointer"
              >
                Get started
              </Link>
            </SignedOut>
            <SignedIn>
              <Link
                href="/analyze"
                className="text-xs font-semibold bg-cyan-500 text-background rounded-lg px-4 py-2 hover:bg-cyan-400 transition-colors cursor-pointer"
              >
                Dashboard
              </Link>
            </SignedIn>
          </div>
        </nav>
      </header>

      {/* Hero */}
      <section className="relative pt-40 pb-24 px-6 text-center max-w-5xl mx-auto">
        {/* Badge */}
        <div className="inline-flex items-center gap-1.5 border border-cyan-500/25 bg-cyan-500/5 text-cyan-400 rounded-full px-3 py-1 text-xs font-medium mb-8">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse-slow" />
          AI-powered cloud repatriation
        </div>

        {/* Headline */}
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.05] mb-6">
          <span className="text-gradient">Exit hyperscalers.</span>
          <br />
          <span className="text-foreground/90">Own your infra.</span>
        </h1>

        <p className="text-base md:text-lg text-muted-foreground max-w-xl mx-auto mb-10 leading-relaxed">
          Kandha gives SMB and mid-market SaaS teams an AI-guided path from AWS, GCP, or Azure
          to bare-metal servers — cutting costs by 50%+ in days, not months.
        </p>

        <div className="flex items-center justify-center gap-3 flex-wrap">
          <SignedOut>
            <Link
              href="/sign-up"
              className="inline-flex items-center gap-2 bg-cyan-500 text-background rounded-xl px-6 py-3 text-sm font-semibold hover:bg-cyan-400 transition-all hover:shadow-[0_0_20px_hsl(189_100%_53%/0.3)] cursor-pointer"
            >
              Analyze your cloud bill
              <ArrowRightIcon />
            </Link>
          </SignedOut>
          <SignedIn>
            <Link
              href="/analyze"
              className="inline-flex items-center gap-2 bg-cyan-500 text-background rounded-xl px-6 py-3 text-sm font-semibold hover:bg-cyan-400 transition-all hover:shadow-[0_0_20px_hsl(189_100%_53%/0.3)] cursor-pointer"
            >
              Go to dashboard
              <ArrowRightIcon />
            </Link>
          </SignedIn>
          <a
            href="#features"
            className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors border border-border/60 rounded-xl px-6 py-3 hover:border-border cursor-pointer"
          >
            See how it works
          </a>
        </div>

        {/* Stats row */}
        <div className="mt-16 grid grid-cols-3 gap-px max-w-lg mx-auto rounded-xl overflow-hidden border border-border/50">
          {stats.map((s) => (
            <div key={s.label} className="bg-card/50 px-6 py-4 text-center">
              <div className="text-2xl font-bold font-mono text-gradient">{s.value}</div>
              <div className="text-xs text-muted-foreground mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Terminal preview strip */}
      <section className="px-6 pb-24 max-w-4xl mx-auto">
        <div className="glass-bright rounded-2xl overflow-hidden border border-border/60">
          {/* Terminal header */}
          <div className="flex items-center gap-2 px-4 py-3 border-b border-border/50 bg-card/30">
            <span className="w-3 h-3 rounded-full bg-red-500/60" />
            <span className="w-3 h-3 rounded-full bg-amber-500/60" />
            <span className="w-3 h-3 rounded-full bg-emerald-500/60" />
            <span className="ml-3 text-xs text-muted-foreground font-mono">kandha — repatriation-agent</span>
          </div>
          {/* Terminal body */}
          <div className="p-6 font-mono text-sm space-y-2 leading-relaxed">
            <div>
              <span className="text-cyan-400">$</span>
              <span className="text-muted-foreground"> kandha analyze --bill aws-invoice-oct-2024.csv</span>
            </div>
            <div className="text-muted-foreground/60 pl-3">Parsing 847 line items across 12 services...</div>
            <div className="text-muted-foreground/60 pl-3">Querying Hetzner + OVH pricing API...</div>
            <div className="text-emerald-400 pl-3">✓ Analysis complete in 3.2s</div>
            <div className="mt-3 pl-3 border-l border-border">
              <div className="text-foreground/80">Current monthly spend: <span className="text-foreground font-semibold">$18,420</span></div>
              <div className="text-foreground/80">Projected bare-metal cost: <span className="text-emerald-400 font-semibold">$6,800</span></div>
              <div className="text-foreground/80">Estimated annual savings: <span className="text-emerald-400 font-semibold">$138,240</span></div>
              <div className="text-foreground/80">Recommended: <span className="text-cyan-400">Hetzner AX162 × 3 nodes</span></div>
            </div>
            <div className="mt-2">
              <span className="text-cyan-400">$</span>
              <span className="text-muted-foreground"> kandha agent --session new</span>
            </div>
            <div className="text-cyan-400/70 cursor-blink pl-3">Ready to build your migration plan</div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="px-6 pb-24 max-w-5xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-gradient-subtle mb-3">
            Three tools. One migration.
          </h2>
          <p className="text-muted-foreground text-sm max-w-md mx-auto">
            From cost analysis to live deployment — everything you need to leave the hyperscaler.
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-4">
          {features.map((f) => (
            <div
              key={f.title}
              className="glass rounded-2xl p-6 hover:border-cyan-500/20 hover:shadow-[0_0_30px_hsl(189_100%_53%/0.06)] transition-all duration-300 group cursor-default"
            >
              <div className="w-10 h-10 rounded-xl bg-cyan-500/10 flex items-center justify-center mb-4 group-hover:bg-cyan-500/15 transition-colors">
                <f.Icon className="w-5 h-5 text-cyan-400" />
              </div>
              <div className="inline-flex items-center gap-1.5 mb-3">
                <span className="text-xs font-mono text-cyan-500/70">0{f.step}</span>
                <span className="text-xs text-muted-foreground/50">/</span>
              </div>
              <h3 className="text-base font-semibold text-foreground mb-2">{f.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{f.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="px-6 pb-24 max-w-4xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-gradient-subtle mb-3">
            From bill to bare metal in days
          </h2>
        </div>
        <div className="relative">
          {/* Connecting line */}
          <div className="absolute left-[39px] top-10 bottom-10 w-px bg-gradient-to-b from-cyan-500/30 via-emerald-400/20 to-transparent hidden md:block" />
          <div className="space-y-6">
            {steps.map((s, i) => (
              <div key={s.title} className="flex items-start gap-5">
                <div className="w-20 h-10 shrink-0 flex items-center justify-center">
                  <div className="w-8 h-8 rounded-full border border-cyan-500/30 bg-cyan-500/10 flex items-center justify-center text-xs font-mono font-bold text-cyan-400">
                    {i + 1}
                  </div>
                </div>
                <div className="glass rounded-xl p-5 flex-1">
                  <div className="text-sm font-semibold text-foreground mb-1">{s.title}</div>
                  <div className="text-xs text-muted-foreground">{s.description}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 pb-24 max-w-3xl mx-auto text-center">
        <div className="glass rounded-2xl px-8 py-12 border border-cyan-500/10 relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-radial from-cyan-500/5 via-transparent to-transparent" />
          <div className="relative">
            <h2 className="text-3xl font-bold tracking-tight mb-3 text-gradient-subtle">
              Ready to cut your cloud bill in half?
            </h2>
            <p className="text-sm text-muted-foreground mb-8 max-w-md mx-auto">
              Upload your first bill for free. No credit card required.
            </p>
            <SignedOut>
              <Link
                href="/sign-up"
                className="inline-flex items-center gap-2 bg-cyan-500 text-background rounded-xl px-8 py-3.5 text-sm font-semibold hover:bg-cyan-400 transition-all hover:shadow-[0_0_30px_hsl(189_100%_53%/0.35)] cursor-pointer"
              >
                Start free analysis
                <ArrowRightIcon />
              </Link>
            </SignedOut>
            <SignedIn>
              <Link
                href="/analyze"
                className="inline-flex items-center gap-2 bg-cyan-500 text-background rounded-xl px-8 py-3.5 text-sm font-semibold hover:bg-cyan-400 transition-all cursor-pointer"
              >
                Go to dashboard
                <ArrowRightIcon />
              </Link>
            </SignedIn>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/40 py-8 px-6 text-center">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <KandhaLogo />
            <span className="text-xs font-semibold text-foreground/70">Kandha</span>
          </div>
          <span className="text-xs text-muted-foreground">
            © {new Date().getFullYear()} Kandha. Built to set your infrastructure free.
          </span>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <a href="#" className="hover:text-foreground transition-colors cursor-pointer">Privacy</a>
            <a href="#" className="hover:text-foreground transition-colors cursor-pointer">Terms</a>
            <a href="#" className="hover:text-foreground transition-colors cursor-pointer">Docs</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

// ─── Data ────────────────────────────────────────────────────────────────────

const stats = [
  { value: "50%+", label: "Cost reduction" },
  { value: "3 days", label: "Avg. migration" },
  { value: "99.9%", label: "Uptime SLA" },
];

const features = [
  {
    step: 1,
    title: "Cost Analyzer",
    description:
      "Upload any AWS, GCP, or Azure bill. Get instant spend breakdown, idle resource detection, and a precise savings estimate with hardware recommendations.",
    Icon: BarChartIcon,
  },
  {
    step: 2,
    title: "Repatriation Agent",
    description:
      "AI agent that audits your architecture and builds a sequenced, risk-flagged migration plan. Memory persists across sessions — context never lost.",
    Icon: AgentIcon,
  },
  {
    step: 3,
    title: "Infra Configurator",
    description:
      "Pick provider, region, and workload type. Get production-ready K3s manifests, Helm values, and a one-click deploy script — in seconds.",
    Icon: InfraIcon,
  },
];

const steps = [
  {
    title: "Upload your cloud bill",
    description:
      "Drop a CSV export from AWS Cost Explorer, GCP Billing, or Azure Cost Management. Kandha parses it instantly.",
  },
  {
    title: "Get your savings report",
    description:
      "AI breaks down your spend by service, flags idle resources, and shows projected costs on Hetzner or OVH hardware.",
  },
  {
    title: "Chat with the Repatriation Agent",
    description:
      "Describe your stack. The agent audits dependencies, proposes a migration sequence, and flags risks before you touch a server.",
  },
  {
    title: "Generate infra and deploy",
    description:
      "Configure your target cluster in the Infra Configurator. Download manifests or trigger a one-click deploy via SSH + cloud-init.",
  },
];

// ─── Icons (inline SVG — no emoji) ───────────────────────────────────────────

function KandhaLogo() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="text-cyan-400">
      <path
        d="M12 2L3 7v10l9 5 9-5V7L12 2z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M12 2v20M3 7l9 5 9-5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeOpacity="0.4"
      />
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

function BarChartIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <rect x="3" y="9" width="4" height="12" rx="1" />
      <rect x="10" y="5" width="4" height="16" rx="1" />
      <rect x="17" y="1" width="4" height="20" rx="1" />
    </svg>
  );
}

function AgentIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M12 2a4 4 0 0 1 4 4v2a4 4 0 0 1-8 0V6a4 4 0 0 1 4-4z" />
      <path d="M9 11.5V13a3 3 0 0 0 6 0v-1.5" />
      <path d="M6 21v-1a6 6 0 0 1 12 0v1" />
      <circle cx="12" cy="12" r="1" fill="currentColor" />
    </svg>
  );
}

function InfraIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <rect x="2" y="3" width="20" height="6" rx="2" />
      <rect x="2" y="12" width="20" height="6" rx="2" />
      <circle cx="6" cy="6" r="1" fill="currentColor" stroke="none" />
      <circle cx="6" cy="15" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}
