// Dashboard shell — dark sidebar with SVG icons and Clerk user button
"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth, UserButton } from "@clerk/nextjs";
import { setAuthTokenProvider } from "@/lib/api";

const navLinks = [
  {
    href: "/analyze",
    label: "Cost Analyzer",
    Icon: BarChartIcon,
    description: "Upload & analyze bills",
  },
  {
    href: "/agent",
    label: "Repatriation Agent",
    Icon: AgentIcon,
    description: "AI migration planner",
  },
  {
    href: "/configure",
    label: "Infra Configurator",
    Icon: InfraIcon,
    description: "Generate K8s manifests",
  },
  {
    href: "/evals",
    label: "Evals",
    Icon: EvalsIcon,
    description: "LLM quality metrics",
  },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { getToken } = useAuth();

  useEffect(() => {
    setAuthTokenProvider(() => getToken());
  }, [getToken]);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <aside className="w-56 flex flex-col shrink-0 border-r border-border/50 bg-card/30">
        {/* Logo */}
        <div className="px-4 py-5 border-b border-border/50">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="w-7 h-7 rounded-lg bg-cyan-500/15 border border-cyan-500/20 flex items-center justify-center group-hover:bg-cyan-500/20 transition-colors">
              <KandhaLogo />
            </div>
            <span className="text-sm font-bold tracking-tight text-foreground">Kandha</span>
          </Link>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 py-3 space-y-0.5">
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all cursor-pointer group ${
                  isActive
                    ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/15"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent/50 border border-transparent"
                }`}
              >
                <link.Icon
                  className={`w-4 h-4 shrink-0 transition-colors ${
                    isActive ? "text-cyan-400" : "text-muted-foreground group-hover:text-foreground"
                  }`}
                />
                <span className="font-medium truncate">{link.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Status indicator */}
        <div className="px-3 py-3 mx-2 mb-2 rounded-lg bg-muted/30 border border-border/40">
          <div className="flex items-center gap-2 mb-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-emerald-400 font-medium">API online</span>
          </div>
          <div className="text-xs text-muted-foreground font-mono truncate">
            kimi-k2-5 · ready
          </div>
        </div>

        {/* User */}
        <div className="px-4 py-4 border-t border-border/50">
          <UserButton afterSignOutUrl="/" showName />
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto bg-background bg-dot-grid">{children}</main>
    </div>
  );
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function KandhaLogo() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-cyan-400">
      <path d="M12 2L3 7v10l9 5 9-5V7L12 2z" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round" />
      <path d="M12 2v20M3 7l9 5 9-5" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round" strokeOpacity="0.4" />
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
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
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

function EvalsIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
    </svg>
  );
}
