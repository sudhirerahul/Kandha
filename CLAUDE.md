# CLAUDE.md — Kandha: Cloud Repatriation Kit

> This file is the source of truth for all Claude Code sessions on this project.
> Read it fully before writing any code. Never deviate from the conventions here.

---

## 🧭 Project North Star

**Kandha** is a cloud repatriation platform that makes bare-metal servers (Hetzner, OVH, on-prem) feel like AWS — deployed in one click.

It gives SMB and mid-market SaaS companies a clear, AI-assisted path to exit hyperscalers and cut infrastructure costs by 50%+.

**Three core product surfaces:**
1. **Cost Analyzer** — Parse cloud bills → output savings estimate + hardware recommendation
2. **Repatriation Agent** — AI agent that audits architecture and builds a migration plan
3. **Infra Configurator** — 1-click Kubernetes stack generation for bare metal

---

## 🏗️ Tech Stack

### Infrastructure (Target Deployment)
- **Compute**: Hetzner Cloud / OVH / On-prem bare metal
- **Orchestration**: Kubernetes (K3s for lightweight, K8s for production)
- **Ingress**: Traefik or NGINX Ingress Controller
- **Monitoring**: Prometheus + Grafana (pre-configured)
- **Databases**: PostgreSQL, Redis (Helm charts)
- **CI/CD**: ArgoCD (GitOps)
- **Object Storage**: MinIO (S3-compatible)

### AI Layer
- **Inference**: GMI Cloud (NVIDIA partner) — endpoint for Kimi K2
- **Model**: Kimi K2.5 (native multimodal agentic reasoning via GMI)
- **Orchestration**: Dify (agentic workflows, RAG pipelines, observability)
- **Memory**: HydraDB (persistent agent memory across sessions)
- **Distribution**: Photon (agent-to-interface delivery)

### Application Stack
- **Frontend**: Next.js 14 (App Router) + Tailwind CSS
- **Backend**: FastAPI (Python 3.11+)
- **API Layer**: REST + WebSocket for streaming agent responses
- **Auth**: Clerk or Auth.js
- **DB (App)**: PostgreSQL via Prisma (frontend) / SQLAlchemy (backend)
- **Queue**: Redis + BullMQ for async infra jobs
- **File handling**: S3-compatible (MinIO or Cloudflare R2)

### Dev Tooling
- **Package manager**: pnpm (frontend), uv (Python)
- **Monorepo**: Turborepo
- **Linting**: ESLint + Prettier (frontend), Ruff (Python)
- **Testing**: Vitest (frontend), Pytest (backend)
- **Containerization**: Docker + Docker Compose for local dev
- **IaC**: Pulumi (TypeScript) or Terraform for provisioning scripts

---

## 📁 Repository Structure

```
kandha/
├── apps/
│   ├── web/                  # Next.js frontend
│   │   ├── app/              # App Router pages
│   │   │   ├── (marketing)/  # Landing, pricing
│   │   │   ├── (dashboard)/  # Authed product UI
│   │   │   │   ├── analyze/  # Cost Analyzer
│   │   │   │   ├── agent/    # Repatriation Agent chat
│   │   │   │   └── configure/ # Infra Configurator
│   │   ├── components/
│   │   │   ├── ui/           # shadcn/ui base components
│   │   │   ├── analyzer/     # Cost Analyzer components
│   │   │   ├── agent/        # Chat UI components
│   │   │   └── configurator/ # Infra form components
│   │   └── lib/
│   └── api/                  # FastAPI backend
│       ├── routers/
│       │   ├── analyze.py    # Bill parsing endpoints
│       │   ├── agent.py      # Repatriation agent endpoints
│       │   └── infra.py      # Infra config endpoints
│       ├── services/
│       │   ├── gmi.py        # GMI Cloud / Kimi K2 client
│       │   ├── dify.py       # Dify workflow client
│       │   ├── hydra.py      # HydraDB memory client
│       │   └── parser.py     # Cloud bill parsing logic
│       ├── models/           # SQLAlchemy models
│       └── main.py
├── packages/
│   ├── ui/                   # Shared design system
│   ├── types/                # Shared TypeScript types
│   └── config/               # Shared ESLint/TS configs
├── infra/
│   ├── k8s/                  # Kubernetes manifests
│   ├── helm/                 # Helm chart templates
│   ├── scripts/              # Bare metal setup scripts
│   └── pulumi/               # IaC for provisioning
├── docker-compose.yml
├── turbo.json
└── CLAUDE.md                 # ← you are here
```

---

## 🔑 Environment Variables

### Frontend (`apps/web/.env.local`)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=
DATABASE_URL=postgresql://kandha:kandha@localhost:5432/kandha
```

### Backend (`apps/api/.env`)
```
# GMI Cloud / Kimi K2
GMI_API_KEY=
GMI_BASE_URL=https://api.gmi.ai/v1
GMI_MODEL=kimi-k2-5

# Dify
DIFY_API_KEY=
DIFY_BASE_URL=https://api.dify.ai/v1
DIFY_WORKFLOW_ID_ANALYZE=
DIFY_WORKFLOW_ID_MIGRATE=

# HydraDB
HYDRA_API_KEY=
HYDRA_BASE_URL=

# Photon
PHOTON_API_KEY=

# App
DATABASE_URL=postgresql://kandha:kandha@localhost:5432/kandha
REDIS_URL=redis://localhost:6379
SECRET_KEY=
```

---

## 🧱 Core Conventions

### General
- Always write TypeScript. No `.js` files in `apps/web`.
- Always write Python with type hints. No untyped functions.
- Every file gets a one-line docstring or comment at the top describing its purpose.
- Prefer composition over inheritance everywhere.
- No premature abstraction — write the simplest thing that works first.

### Frontend
- Use App Router only. No `pages/` directory.
- Use `server components` by default. Add `"use client"` only when necessary (interactivity, hooks).
- Use `shadcn/ui` for base components. Extend with Tailwind; never inline raw CSS.
- All data fetching in server components via `fetch()` with proper caching strategy.
- Forms use `react-hook-form` + `zod` validation — always.
- Use `nuqs` for URL state management (search params).
- Streaming AI responses via the Vercel AI SDK or native ReadableStream.

### Backend
- FastAPI with async handlers (`async def`) always.
- Pydantic v2 for all request/response models — no raw dicts in route handlers.
- Use dependency injection (`Depends`) for auth, DB sessions, service clients.
- All external API calls (GMI, Dify, HydraDB) go through `services/` — never inline in routers.
- Errors: raise `HTTPException` with structured `detail` dicts, not plain strings.
- Logging: use Python `structlog` with JSON output.

### AI / Agent Patterns
- Every agent session gets a `session_id` (UUID) stored in HydraDB.
- Memory writes happen after each agent turn — never skip this.
- Stream Kimi K2 responses via SSE to the frontend — never wait for full completion.
- Dify workflows are the orchestration layer — don't replicate workflow logic in FastAPI.
- All prompts live in `apps/api/prompts/` as `.md` files. Never hardcode prompts in Python.

### Infrastructure Scripts
- All bare-metal setup scripts are idempotent bash (can run twice safely).
- Scripts in `infra/scripts/` follow naming: `01-base.sh`, `02-k3s.sh`, etc.
- Every Helm chart override goes in `infra/helm/values/` — never modify upstream charts.

---

## 🚀 Build Order (Phased)

### Phase 1 — Foundation (Week 1)
- [ ] Monorepo setup (Turborepo, pnpm workspaces)
- [ ] Docker Compose: PostgreSQL, Redis, pgAdmin
- [ ] FastAPI skeleton with health check
- [ ] Next.js skeleton with auth (Clerk)
- [ ] GMI/Kimi K2 client — test inference call
- [ ] Dify client — test workflow trigger
- [ ] HydraDB client — test memory read/write

### Phase 2 — Cost Analyzer (Week 2)
- [ ] Cloud bill upload UI (CSV/JSON)
- [ ] Bill parser service (AWS Cost Explorer export, Azure billing CSV)
- [ ] Cost breakdown model (compute, storage, egress, idle)
- [ ] Hetzner/OVH pricing comparison engine
- [ ] Savings report generation via Kimi K2
- [ ] PDF export of report

### Phase 3 — Repatriation Agent (Week 3)
- [ ] Chat UI with streaming
- [ ] Dify workflow: architecture audit
- [ ] HydraDB session memory integration
- [ ] Migration plan generation (sequenced, risk-flagged)
- [ ] Plan export (Markdown + PDF)

### Phase 4 — Infra Configurator (Week 4)
- [ ] Server picker UI (provider, region, size)
- [ ] Workload type selector (web, ML, database-heavy)
- [ ] K3s/K8s manifest generator
- [ ] Helm values generator
- [ ] One-click deploy via SSH + cloud-init script
- [ ] Deployment status polling UI

### Phase 5 — Polish & GTM (Week 5)
- [ ] Marketing landing page
- [ ] Waitlist / early access flow
- [ ] Onboarding flow (connect cloud account → run audit)
- [ ] Photon integration (agent on Slack/web widget)
- [ ] Monitoring dashboard (Grafana embed)

---

## ⚠️ Things Claude Must Never Do

- Never commit secrets or API keys — use `.env` files always
- Never use `any` type in TypeScript
- Never make synchronous HTTP calls in FastAPI async handlers
- Never write migration SQL by hand — always use Alembic
- Never skip error handling on external API calls (GMI, Dify, HydraDB may fail)
- Never build a new UI component if a shadcn/ui one exists
- Never modify files in `packages/ui` without noting it as a shared change
- Never hardcode provider pricing — always fetch from a config or API

---

## 🧪 Running Locally

```bash
# Clone and install
git clone https://github.com/your-org/kandha
cd kandha
pnpm install

# Start infrastructure
docker-compose up -d

# Run migrations
cd apps/api && uv run alembic upgrade head

# Start all apps
pnpm dev
# → web: http://localhost:3000
# → api: http://localhost:8000
# → api docs: http://localhost:8000/docs
```

---

## 📎 Key Reference Links

- GMI Cloud Docs: https://docs.gmi.ai
- Dify Docs: https://docs.dify.ai
- HydraDB Docs: (add when available)
- Photon Docs: (add when available)
- Hetzner Cloud API: https://docs.hetzner.cloud
- K3s Quickstart: https://docs.k3s.io/quick-start
- shadcn/ui: https://ui.shadcn.com
- Turborepo: https://turbo.build/repo/docs
