# Autonomous Product Factory (APF)

[![CI](https://github.com/Zackanduril/autonomous-product-factory/actions/workflows/ci.yml/badge.svg)](https://github.com/Zackanduril/autonomous-product-factory/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![React 18](https://img.shields.io/badge/react-18-blue.svg)](https://react.dev)
[![Tests](https://img.shields.io/badge/tests-226%20passing-brightgreen.svg)](#test-instructions)

> **Give it an idea. Get back a pull request.**

APF transforms a plain-English product idea into a merge-ready GitHub pull request — complete with a PRD, architecture document, market analysis, UX spec, implementation plan, working code, tests, CI/CD configuration, and auto-generated documentation — in a single command, in under 15 minutes.

```bash
apf run "build a REST API for a subscription billing service"
```

```
[APF] Pipeline run-abc123 started
[PRD        ] Completed in 14s  — executive summary, features, success metrics
[ARCHITECT  ] Completed in 22s  — system design, service map, data model, ADRs
[MARKET     ] Completed in 18s  — competitor table, positioning, pricing model
[UX         ] Completed in 16s  — user flows, wireframe descriptions, components
[ENGINEERING] Completed in 20s  — 20-week milestone plan, team sizing, stack
[DEVELOPER  ] Completed in 47s  — implementation + tests (Python/FastAPI/React)
[QA         ] Completed in 19s  — QA strategy, test cases, coverage plan
[REGRESSION ] Completed in 12s  — regression suite, edge cases, load scenarios
[REVIEW     ] Completed in 11s  — code review, security audit, approval gate
[DEVOPS     ] Completed in 14s  — Dockerfile, GitHub Actions CI, deploy scripts
[README     ] Completed in 9s   — full public README for the generated project

[APF] Pipeline completed in 3m 22s
      PR:        https://github.com/yourorg/yourrepo/pull/47
      Dashboard: http://localhost:3000/pipelines/run-abc123
```

---

## Table of Contents

1. [What APF Builds](#what-apf-builds)
2. [How It Works — The 11-Stage Pipeline](#how-it-works--the-11-stage-pipeline)
3. [Architecture](#architecture)
4. [Service Map](#service-map)
5. [Quick Start](#quick-start)
6. [Configuration Reference](#configuration-reference)
7. [The Dashboard](#the-dashboard)
8. [CLI Reference](#cli-reference)
9. [Connectors](#connectors)
   - [Slack](#slack-connector)
   - [Jira](#jira-connector)
   - [Confluence](#confluence-connector)
   - [AWS](#aws-connector)
   - [GitHub](#github-connector)
10. [LLM Providers](#llm-providers)
11. [Development Setup](#development-setup)
12. [Test Instructions](#test-instructions)
13. [Project Structure](#project-structure)
14. [Contribution Guidelines](#contribution-guidelines)
15. [FAQ](#faq)
16. [License](#license)

---

## What APF Builds

For every idea you submit, APF produces a set of **artifacts** — structured documents and code files stored and versioned in the artifact store. Each artifact is the output of one of the eleven specialist agents.

| Stage | Agent | What It Produces |
|---|---|---|
| 1 | **PRD Agent** | Product Requirements Document — executive summary, target users, core features list, success metrics, out-of-scope items, risks |
| 2 | **Architect Agent** | Architecture document — system design, service decomposition, data model, API contracts, ADRs, security model |
| 3 | **Market Agent** | Market analysis — competitor table, TAM/SAM/SOM, positioning statement, pricing model, go-to-market strategy |
| 4 | **UX Agent** | UX specification — user personas, user flows, wireframe descriptions, component inventory, accessibility checklist |
| 5 | **Engineering Agent** | Engineering plan — 20-week milestone roadmap, team sizing, technology stack rationale, risk register |
| 6 | **Developer Agent** | Implementation — working source code, unit tests, project scaffold, dependency manifest |
| 7 | **QA Agent** | QA strategy — test plan, test cases for every feature, coverage targets, test environment requirements |
| 8 | **Regression Agent** | Regression suite — regression test matrix, edge cases, performance benchmarks, chaos scenarios |
| 9 | **Review Agent** | Code review — security audit (OWASP Top 10 check), style review, approval/reject verdict with comments |
| 10 | **DevOps Agent** | DevOps package — Dockerfile, Docker Compose, GitHub Actions CI workflow, deploy scripts, health checks |
| 11 | **README Agent** | Public README — installation guide, usage examples, API reference, contributing guide for the generated project |

All artifacts are stored as versioned, content-addressed records in the artifact store and are downloadable via the CLI or dashboard at any time.

---

## How It Works — The 11-Stage Pipeline

### Pipeline Execution Flow

```
 Idea (string)
     │
     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          Orchestrator (DAG Engine)                            │
│                                                                                │
│  Stage 1          Stage 2          Stage 3          Stage 4          Stage 5  │
│  ┌───────┐        ┌───────┐        ┌───────┐        ┌───────┐        ┌──────┐│
│  │  PRD  │───────▶│Archit.│──┬────▶│Market │        │  UX   │        │ Eng. ││
│  └───────┘        └───────┘  │     └───────┘        └───────┘        └──────┘│
│                               │                                               │
│                               │     Stage 6                                   │
│                               └────▶┌─────────┐                              │
│                                     │Developer│                              │
│                                     └────┬────┘                              │
│                                          │                                    │
│                              ┌───────────┼───────────┐                       │
│                              ▼           ▼           ▼                       │
│                          Stage 7      Stage 9      Stage 10                  │
│                          ┌─────┐      ┌──────┐     ┌──────┐                 │
│                          │ QA  │      │Review│     │DevOps│                 │
│                          └──┬──┘      └──┬───┘     └──┬───┘                 │
│                             │            │             │                      │
│                             ▼            │             │                      │
│                         Stage 8          │             │                      │
│                         ┌──────────┐     │             │                      │
│                         │Regression│     │             │                      │
│                         └────┬─────┘     │             │                      │
│                              └─────┬─────┘─────────────┘                     │
│                                    ▼                                          │
│                                Stage 11                                       │
│                                ┌────────┐                                    │
│                                │ README │                                    │
│                                └────┬───┘                                    │
└─────────────────────────────────────┼────────────────────────────────────────┘
                                      │
                                      ▼
                              GitHub Pull Request
```

### The Orchestrator DAG

The pipeline is not a simple linear chain — the orchestrator executes stages as a **directed acyclic graph (DAG)**. Stages that don't depend on each other can run in parallel. The DAG also enforces quality gates: the Review agent can block the PR creation stage and trigger a targeted re-run of the Developer agent if it finds critical issues.

**Stage dependencies:**

| Stage | Depends On |
|---|---|
| PRD | — (root) |
| Architect | PRD |
| Market | PRD |
| UX | PRD |
| Engineering | Architect |
| Developer | Architect, Engineering |
| QA | Developer |
| Regression | QA |
| Review | Developer |
| DevOps | Developer |
| README | PRD, Architect, QA, DevOps |

### Human-in-the-Loop (HITL) Gates

By default, APF runs fully autonomously. You can insert a manual approval gate at any stage:

```bash
# Run with a Slack approval gate before the PR is created
apf run "build an auth service" --approve-before readme
```

When a gate is reached, APF sends a Slack Block Kit message with Approve / Reject buttons. Rejecting a gate lets you add a comment that is fed back into the next agent call as context.

### Context Propagation

Every agent receives the **full pipeline context** — the idea string and all previously produced artifacts. This means the Developer agent sees the PRD, architecture, market analysis, UX spec, and engineering plan before writing a single line of code. Each agent is a specialist that builds on the work of all agents before it.

---

## Architecture

APF is a polyglot microservices system. All backend services are **Python 3.12 + FastAPI**. The web dashboard is **React 18 + TypeScript + Vite**. Services communicate via **Redis Streams** (event bus) and expose REST/WebSocket APIs.

```
                 ┌────────────────────────────────────────────────────────────────────┐
                 │                           APF Platform                              │
                 │                                                                      │
  ┌──────────┐   │  ┌──────────────┐    ┌────────────────┐    ┌──────────────────┐   │
  │   CLI    │──▶│  │ orchestrator │───▶│  agent-runner  │───▶│  artifact-store  │   │
  │ (Click)  │   │  │  :8000       │    │  (pool worker) │    │  :8001           │   │
  └──────────┘   │  └──────┬───────┘    └────────────────┘    └──────────────────┘   │
                 │         │                                                            │
  ┌──────────┐   │  ┌──────▼───────┐                                                  │
  │ Browser  │──▶│  │ dashboard-ui │    ┌──────────────────────────────────────────┐  │
  └──────────┘   │  │   :3000      │    │        Event Bus (Redis Streams)          │  │
                 │  └──────────────┘    │  apf:stage:dispatch                       │  │
                 │                      │  apf:stage:result  apf:stage:log          │  │
  ┌──────────┐   │                      │  apf:pipeline:status                      │  │
  │  GitHub  │──▶│                      │  apf:pipeline:approval                   │  │
  │ Webhooks │   │                      │  apf:connector:action                     │  │
  └──────────┘   │                      └──────────────────────────────────────────┘  │
                 │                                                                      │
  ┌──────────┐   │  ┌──────────────────────────────────────────────────────────────┐  │
  │  Slack   │──▶│  │                        Connectors                             │  │
  └──────────┘   │  │  github-integration :8002   slack-connector :8003            │  │
                 │  │  jira-connector :8004        confluence-connector :8005       │  │
                 │  │  aws-connector :8006                                          │  │
                 │  └──────────────────────────────────────────────────────────────┘  │
                 │                                                                      │
                 │  ┌────────────────────────────────────────────────────────────────┐ │
                 │  │   PostgreSQL / SQLite      Redis 7       MinIO / S3             │ │
                 │  └────────────────────────────────────────────────────────────────┘ │
                 └────────────────────────────────────────────────────────────────────┘
```

**Key design decisions:**

- **Microservices with Docker profiles** — connectors are independently deployable. Omit a profile and that service simply doesn't start. Core pipeline (orchestrator + agent-runner + artifact-store) runs without any connectors.
- **Redis Streams as event bus** — Redis is already required; Streams give at-least-once delivery, consumer groups, and replay without adding a second broker (Kafka, RabbitMQ).
- **SQLite / PostgreSQL dual support** — identical SQLAlchemy 2.x async ORM code targets both. Switch with a single env var change and `alembic upgrade head`.
- **LLM provider abstraction** — a `LLMProvider` Protocol (`complete()`, `structured_output()`) means you can swap Anthropic → OpenAI → any LiteLLM-compatible model with one config change.
- **Content-addressed artifact store** — every artifact is SHA-256 hashed on write. Identical content is deduplicated. All versions are retained and queryable.

---

## Service Map

| Service | Port | Stack | Role |
|---|---|---|---|
| `orchestrator` | 8000 | Python / FastAPI / SQLAlchemy | Core runtime: DAG execution, stage dispatch, retries, HITL gates, REST + WebSocket API, JWT auth |
| `agent-runner` | internal | Python / FastAPI | Worker: LLM prompt rendering, streaming completions, artifact validation, SAST secret scanning |
| `artifact-store` | 8001 | Python / FastAPI | Versioned artifact storage — local filesystem or S3-compatible backend |
| `dashboard` | 3000 | React 18 / Vite / Tailwind | Web UI: pipeline list, stage timeline, live WebSocket updates, integrations page |
| `github-integration` | 8002 | Python / FastAPI | GitHub App webhooks, branch creation, PR creation, HMAC validation |
| `slack-connector` | 8003 | Python / FastAPI | Block Kit notifications, HITL approval buttons, `/apf` slash command |
| `jira-connector` | 8004 | Python / FastAPI | Auto-create Jira issues per stage, transition statuses, add comments |
| `confluence-connector` | 8005 | Python / FastAPI | Publish artifacts as Confluence pages (markdown → Storage Format) |
| `aws-connector` | 8006 | Python / FastAPI / boto3 | Trigger ECS rolling deployments after PR merge |
| `PostgreSQL` | 5432 | — | Primary relational store (pipelines, stages, artifacts, users, audit log) |
| `Redis` | 6379 | — | Event bus (Streams), session cache, WebSocket pub/sub |
| `MinIO` | 9000/9001 | — | S3-compatible artifact blob store (dev / self-hosted) |

---

## Quick Start

### Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Docker | 26+ | Required for `docker compose` |
| Docker Compose | v2 (plugin) | `docker compose`, not `docker-compose` |
| An LLM API key | — | Anthropic (recommended) or OpenAI |
| Git | 2+ | For cloning |

### 1. Clone and configure

```bash
git clone https://github.com/Zackanduril/autonomous-product-factory.git
cd autonomous-product-factory
cp deploy/.env.example deploy/.env
```

Open `deploy/.env` and fill in at minimum:

```env
APF_SECRET_KEY=<run: openssl rand -hex 32>
APF_ADMIN_PASSWORD=changeme

LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

GITHUB_APP_ID=...
GITHUB_APP_PRIVATE_KEY=...
GITHUB_APP_INSTALLATION_ID=...
GITHUB_DEFAULT_REPO=yourorg/yourrepo
```

### 2. Start the core stack

```bash
docker compose -f deploy/docker-compose.yml up
```

The stack starts: orchestrator, agent-runner, artifact-store, dashboard, Redis, PostgreSQL, MinIO.

- **Dashboard:** http://localhost:3000 (login: `admin` / your `APF_ADMIN_PASSWORD`)
- **API docs:** http://localhost:8000/docs

### 3. Install the CLI

```bash
pip install apf-cli
# or from this repo:
pip install ./cli
```

### 4. Authenticate and run

```bash
apf auth login
apf run "build a REST API for a task management app"
```

Watch the pipeline run in your terminal. When it completes, a pull request URL is printed.

### Adding Optional Connectors

Connectors are activated via Docker Compose profiles. Add the relevant env vars to `deploy/.env` first, then:

```bash
# Slack + Jira only
docker compose -f deploy/docker-compose.yml --profile slack --profile jira up

# All connectors
docker compose -f deploy/docker-compose.yml \
  --profile slack --profile jira --profile confluence --profile aws up
```

---

## Configuration Reference

All configuration is via environment variables in `deploy/.env` (or injected as CI secrets). No secrets are stored in config files.

### Core Services

| Variable | Required | Default | Description |
|---|---|---|---|
| `APF_SECRET_KEY` | **Yes** | — | Random secret for JWT signing. Generate: `openssl rand -hex 32` |
| `APF_ADMIN_USERNAME` | No | `admin` | Initial admin username |
| `APF_ADMIN_PASSWORD` | **Yes** | — | Initial admin password |
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./apf.db` | PostgreSQL: `postgresql+asyncpg://user:pass@host/apf` |
| `REDIS_URL` | No | `redis://localhost:6379` | Redis connection string |
| `MAX_CONCURRENT_PIPELINES` | No | `5` | Max simultaneous pipeline runs |
| `PIPELINE_RETENTION_DAYS` | No | `90` | Days before pipeline records are purged |

### Artifact Store

| Variable | Required | Default | Description |
|---|---|---|---|
| `ARTIFACT_BACKEND` | No | `local` | `local` or `s3` |
| `LOCAL_STORAGE_PATH` | No | `./artifacts` | Filesystem path when `BACKEND=local` |
| `S3_ENDPOINT_URL` | Cond. | `http://minio:9000` | S3-compatible endpoint (MinIO or real S3) |
| `S3_BUCKET` | Cond. | `apf-artifacts` | Bucket name |
| `AWS_ACCESS_KEY_ID` | Cond. | — | Required when `BACKEND=s3` |
| `AWS_SECRET_ACCESS_KEY` | Cond. | — | Required when `BACKEND=s3` |

### LLM Provider

| Variable | Required | Default | Description |
|---|---|---|---|
| `LLM_PROVIDER` | **Yes** | `anthropic` | `anthropic`, `openai`, or `litellm` |
| `LLM_MODEL` | No | `claude-opus-4-6` | Model identifier |
| `ANTHROPIC_API_KEY` | Cond. | — | Required when `LLM_PROVIDER=anthropic` |
| `OPENAI_API_KEY` | Cond. | — | Required when `LLM_PROVIDER=openai` |
| `LITELLM_BASE_URL` | Cond. | — | Required when `LLM_PROVIDER=litellm` |
| `LLM_MAX_TOKENS` | No | `8192` | Max output tokens per agent call |
| `LLM_TEMPERATURE` | No | `0.3` | Sampling temperature |

---

## The Dashboard

The web dashboard at `http://localhost:3000` provides a real-time view of all pipeline activity.

### Pipelines List

The main screen shows all pipeline runs with their current status:

- **Status badges:** `pending` / `running` (animated) / `paused` / `completed` / `failed` / `cancelled`
- **New Pipeline** button — type your idea and hit Run to start a pipeline from the browser
- Auto-refreshes every 5 seconds

### Pipeline Detail View

Clicking a pipeline opens the detail view:

- **Stage timeline** — all 11 stages rendered in order with status badges and timing
- **Live updates** — the timeline updates in real time via WebSocket (no page refresh needed)
- **Pause / Resume** — pause a running pipeline to inspect its intermediate artifacts before continuing
- **Cancel** — cancel a running or paused pipeline

### Integrations Page

Shows the status of all five connectors (GitHub, Slack, Jira, Confluence, AWS) — which are configured and which are not.

### Authentication

The dashboard uses JWT authentication. Sign in with the admin credentials set in `APF_ADMIN_PASSWORD`. Tokens are persisted in `localStorage` and auto-refreshed.

---

## CLI Reference

```bash
pip install apf-cli
```

### Authentication

```bash
apf auth login                     # Prompt for credentials
apf auth login --token <token>     # Non-interactive (CI)
apf auth whoami                    # Show current user
```

### `apf run` — Start a Pipeline

```bash
# Full 11-stage pipeline
apf run "build a Stripe billing integration"

# Run and watch live output
apf run "build a rate-limiter middleware" --watch

# Insert a manual approval gate before the PR is submitted
apf run "build a payment service" --approve-before readme

# Machine-readable output (newline-delimited JSON events)
apf run "build a metrics dashboard" --json

# Run only a single stage (useful for testing agents)
apf run --stage prd "build a search service"

# Resume a previous pipeline from a specific stage
apf run --resume <PIPELINE_ID> --from developer

# Target a specific repo and branch
apf run "build an auth service" \
  --repo myorg/myrepo \
  --base-branch develop
```

### `apf status` — Check Status

```bash
apf status                          # List all recent pipelines
apf status <PIPELINE_ID>            # Status of a specific pipeline
apf status <PIPELINE_ID> --watch    # Poll until complete
apf status <PIPELINE_ID> --json     # Machine-readable
```

Example output:
```
[APF] Pipeline run-abc123
  Status:   running
  Stage:    developer (6/11)
  Started:  2026-03-25 14:02:11 UTC  (3m 14s ago)
  PR:       —
```

### `apf logs` — Inspect Agent Logs

```bash
apf logs <PIPELINE_ID>                        # Full log
apf logs <PIPELINE_ID> --follow               # Stream live
apf logs <PIPELINE_ID> --stage developer      # One stage only
apf logs <PIPELINE_ID> --stage qa --level error
```

### `apf artifacts` — Download Artifacts

```bash
apf artifacts <PIPELINE_ID>                           # List all artifacts
apf artifacts <PIPELINE_ID> --stage prd               # Show PRD artifact
apf artifacts <PIPELINE_ID> --output ./artifacts/     # Download all to disk
apf artifacts <PIPELINE_ID> --stage developer --output ./code/
```

### `apf config` — Configuration

```bash
apf config init            # Interactive setup wizard
apf config init --global   # Write to ~/.apf/config.yaml
apf config validate        # Validate current config
```

### `apf integrations` — Connector Management

```bash
apf integrations list                    # Show all connectors and status
apf integrations enable slack            # Enable Slack (prompts for tokens)
apf integrations enable jira             # Enable Jira (prompts for tokens)
apf integrations disable aws             # Disable a connector
```

---

## Connectors

Connectors are optional, independently deployable services. None are required for the core pipeline to function. Each is activated via a Docker Compose profile.

### Slack Connector

**What it does:**
- Sends a Block Kit message to your channel when each stage starts and completes
- Sends a pipeline-complete message with the PR URL when the full pipeline finishes
- Delivers an interactive approval message (with Approve / Reject buttons) when a HITL gate is reached
- Handles the `/apf` slash command (future: start a pipeline from Slack)

**Setup:**

1. Create a [Slack App](https://api.slack.com/apps) in your workspace
2. Add Bot Token Scopes: `chat:write`, `chat:write.public`, `commands`
3. Enable Event Subscriptions, set the Request URL to `https://your-apf-host/slack/events`
4. Install the app to your workspace

```env
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
SLACK_CHANNEL=#apf-pipelines
```

```bash
docker compose -f deploy/docker-compose.yml --profile slack up
```

**Notification example (stage complete):**

```
✅  PRD — completed in 14s
Pipeline: Build a billing API
Stage 1/11 | run-abc123
```

---

### Jira Connector

**What it does:**
- Creates a Jira Task for each pipeline stage when it starts, labelled with `apf` and the stage name
- Creates a Jira Story when the full pipeline completes, linking to the PR

**Setup:**

1. Generate a [Jira API token](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Note your Jira project key (e.g., `ENG`)

```env
JIRA_URL=https://yourorg.atlassian.net
JIRA_USER=you@yourorg.com
JIRA_API_TOKEN=...
JIRA_PROJECT_KEY=ENG
```

```bash
docker compose -f deploy/docker-compose.yml --profile jira up
```

**What gets created in Jira:**

- One **Task** per stage: `[APF] PRD — Build a billing API` (labels: `apf`, `prd`)
- One **Story** on completion: `[APF] Pipeline complete — Build a billing API` (with PR link)

---

### Confluence Connector

**What it does:**
- Publishes each stage's artifact as a Confluence page in your chosen space
- Converts Markdown output from agents to Confluence Storage Format (headings, lists, paragraphs)
- Upserts pages — re-running a pipeline updates the existing page rather than creating duplicates
- Publishes a pipeline summary page with a table linking to all individual artifact pages

**Setup:**

1. Generate a [Confluence API token](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Find the numeric ID of the parent page where APF pages should live

```env
CONFLUENCE_URL=https://yourorg.atlassian.net
CONFLUENCE_USER=you@yourorg.com
CONFLUENCE_API_TOKEN=...
CONFLUENCE_SPACE_KEY=DOCS
CONFLUENCE_PARENT_PAGE_ID=123456
```

```bash
docker compose -f deploy/docker-compose.yml --profile confluence up
```

**What gets published:**

- `[APF] PRD — <pipeline_id>` — the full PRD as a Confluence page
- `[APF] ARCHITECT — <pipeline_id>` — architecture document
- ... one page per stage ...
- `[APF] Pipeline Summary — <idea>` — index page with links to all artifact pages

---

### AWS Connector

**What it does:**
- Triggers an ECS rolling deployment when called with a task definition and cluster/service names
- Polls deployment status (running count, desired count, rollout state)
- Can be triggered manually via `POST /deploy` or hooked into the DevOps stage

**Setup:**

Configure AWS credentials with permissions to `ecs:UpdateService` and `ecs:DescribeServices`:

```env
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
AWS_ECS_CLUSTER=my-cluster
AWS_ECS_SERVICE=my-service
AWS_ECS_TASK_DEFINITION=my-task:latest
```

```bash
docker compose -f deploy/docker-compose.yml --profile aws up
```

**API endpoints:**

```
POST /deploy           — trigger ECS rolling deployment
POST /status           — get current deployment status
GET  /healthz          — health check
```

---

### GitHub Connector

**What it does:**
- Receives webhook events from GitHub (push, pull_request, check_run)
- Validates webhook signatures with HMAC-SHA256
- Creates branches and pull requests for completed pipelines
- Handles GitHub App authentication (JWT + installation token)

**Setup:**

1. Create a [GitHub App](https://github.com/settings/apps/new) in your org
2. Grant permissions: `Contents: write`, `Pull requests: write`, `Checks: write`
3. Subscribe to webhook events: `push`, `pull_request`, `check_run`
4. Set the webhook URL to `https://your-apf-host/webhooks/github`

```env
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..."
GITHUB_APP_INSTALLATION_ID=789012
GITHUB_WEBHOOK_SECRET=...
GITHUB_DEFAULT_REPO=yourorg/yourrepo
```

The GitHub connector is included in the core stack (no separate profile needed) — it just needs these env vars to be set.

---

## LLM Providers

APF supports three LLM provider backends, switchable via a single env var.

### Anthropic (Recommended)

```env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-opus-4-6
ANTHROPIC_API_KEY=sk-ant-...
```

Recommended models: `claude-opus-4-6` (highest quality), `claude-sonnet-4-6` (faster, cheaper)

### OpenAI

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...
```

### LiteLLM (Self-hosted / Local)

Use any model supported by [LiteLLM](https://github.com/BerriAI/litellm), including Ollama, Azure OpenAI, Bedrock, Groq, etc.

```env
LLM_PROVIDER=litellm
LLM_MODEL=ollama/llama3
LITELLM_BASE_URL=http://localhost:11434
```

---

## Development Setup

### Python Backend

```bash
# Clone
git clone https://github.com/Zackanduril/autonomous-product-factory.git
cd autonomous-product-factory

# Install uv (Python package manager)
pip install uv

# Install all packages in workspace mode (includes dev dependencies)
uv sync --all-packages --dev

# Install pre-commit hooks
uv run pre-commit install

# Start backing services (Redis + PostgreSQL + MinIO)
docker compose -f deploy/docker-compose.yml up -d redis postgres minio

# Run database migrations
uv run alembic -c packages/db/alembic.ini upgrade head

# Start the orchestrator with hot reload
uv run uvicorn apf_orchestrator.main:app --reload --port 8000

# In a second terminal, start the agent-runner
cd services/agent-runner
uv run uvicorn apf_agent_runner.main:app --reload --port 8010
```

### React Dashboard

```bash
# Install pnpm (Node.js package manager)
npm install -g pnpm

# Install dashboard dependencies
cd services/dashboard
pnpm install

# Start Vite dev server (proxies /api to orchestrator at :8000)
pnpm dev
# Dashboard: http://localhost:3000
```

### Running Individual Services

Each service is a standalone FastAPI app that can be developed and tested independently:

```bash
# Run any service
cd services/<service-name>
pip install -e ".[dev]"
uvicorn apf_<name>.main:app --reload --port <port>
pytest tests/ -v
```

---

## Test Instructions

### Quick: Run All Tests

```bash
# Python tests (all services + packages)
cd services/<name> && python -m pytest tests/ -q

# Or run all at once (requires uv workspace):
uv run pytest packages/ services/ cli/ -m "not integration" -q
```

### Per-Service Test Results (current)

| Suite | Tests | Status | Coverage |
|---|---|---|---|
| `packages/agent-core` | 118 | PASS | — |
| `packages/event-bus` | 8 | PASS | 96% |
| `services/orchestrator` | 28 | PASS | — |
| `services/artifact-store` | 41 | PASS | — |
| `services/agent-runner` | 10 | PASS | — |
| `services/slack-connector` | 6 | PASS | — |
| `services/jira-connector` | 4 | PASS | — |
| `services/confluence-connector` | 3 | PASS | — |
| `services/aws-connector` | 4 | PASS | — |
| **Total** | **226** | **PASS (99.1%)** | — |

### Integration Tests

Integration tests require live Redis and PostgreSQL:

```bash
docker compose -f deploy/docker-compose.yml up -d redis postgres

export DATABASE_URL=postgresql+asyncpg://postgres:test@localhost/apf_test
export REDIS_URL=redis://localhost:6379

uv run pytest services/ packages/ -m "integration" --timeout=120
```

### Dashboard Tests

```bash
cd services/dashboard
pnpm test          # Vitest unit tests
pnpm test:e2e      # Playwright E2E (requires full stack running)
```

### Linting and Type Checking

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy packages/ services/ cli/ --ignore-missing-imports
```

---

## Project Structure

```
autonomous-product-factory/
├── packages/                    # Shared Python libraries
│   ├── agent-core/              # LLM provider abstraction, artifact models, BaseAgent ABC
│   │   ├── apf_agent_core/
│   │   │   ├── agent.py         # BaseAgent (abstract), _call_llm(), structured_output()
│   │   │   ├── artifacts.py     # 11 Pydantic artifact models (PRDArtifact, QAArtifact...)
│   │   │   ├── context.py       # PipelineContext, PipelineConfig, CredentialStore
│   │   │   ├── llm/             # LLMProvider Protocol + Anthropic/OpenAI/LiteLLM impls
│   │   │   └── prompts/         # 11 Jinja2 prompt templates (prd.j2, architect.j2 ...)
│   │   └── tests/               # 118 unit tests
│   ├── db/                      # SQLAlchemy 2.x models + Alembic migrations
│   │   └── apf_db/
│   │       ├── models.py        # Pipeline, Stage, Artifact, AgentRun, User, AuditLog
│   │       ├── session.py       # Async session factory
│   │       └── migrations/      # Alembic env + initial schema migration
│   └── event-bus/               # Redis Streams client + InMemoryEventBus test stub
│       └── apf_event_bus/
│           ├── client.py        # EventBusClient (Redis Streams, consumer groups)
│           ├── memory.py        # InMemoryEventBus (asyncio.Queue — no Redis needed)
│           └── schemas.py       # 9 Pydantic event models
│
├── services/                    # Deployable microservices
│   ├── orchestrator/            # Core pipeline runtime
│   │   └── apf_orchestrator/
│   │       ├── core/
│   │       │   ├── dag.py       # PipelineDAG (networkx), STAGE_DEPS, quality gates
│   │       │   ├── engine.py    # PipelineEngine: create, dispatch, handle events, cancel
│   │       │   └── auth.py      # JWT creation/validation, bcrypt password hashing
│   │       ├── api/             # FastAPI routers: pipelines, stages, connectors, auth, WS
│   │       └── main.py          # App factory + lifespan (DB init, admin seed)
│   ├── agent-runner/            # Agent execution worker
│   │   └── apf_agent_runner/
│   │       ├── agents/          # 11 agent implementations (prd.py, architect.py...)
│   │       ├── sast/            # secret_scan.py — regex + entropy secret detection
│   │       └── runner.py        # Redis Streams consumer loop
│   ├── artifact-store/          # Versioned artifact storage
│   │   └── apf_artifact_store/
│   │       ├── backends/        # local.py (filesystem), s3.py (S3-compatible)
│   │       └── store.py         # ArtifactStore: write, read, list, versions, delete
│   ├── github-integration/      # GitHub App webhook handler
│   ├── slack-connector/         # Slack Block Kit notifications + HITL approvals
│   ├── jira-connector/          # Jira REST API v3 issue creation
│   ├── confluence-connector/    # Confluence REST API page upsert
│   ├── aws-connector/           # AWS ECS deployment via boto3
│   └── dashboard/               # React 18 web dashboard
│       └── src/
│           ├── api/             # Axios API clients (pipelines, auth, connectors)
│           ├── components/      # Layout, StatusBadge, StageTimeline
│           ├── hooks/           # usePipelines, usePipelineWS (WebSocket)
│           ├── pages/           # PipelinesPage, PipelineDetailPage, LoginPage...
│           └── stores/          # Zustand: authStore, pipelineStore
│
├── cli/                         # apf CLI (Click)
│   └── apf_cli/
│       ├── commands/            # run, status, logs, artifacts, config, auth, integrations
│       └── client.py            # httpx.AsyncClient with JWT auth headers
│
├── deploy/
│   ├── docker-compose.yml       # Production: all services + profiles for connectors
│   ├── docker-compose.dev.yml   # Dev override: hot reload, volume mounts
│   └── .env.example             # Template with all variables documented
│
├── docs/
│   ├── prd.md                   # Product Requirements Document
│   ├── architecture.md          # Architecture Decision Records + system design
│   ├── engineering_plan.md      # 20-week milestone plan
│   ├── market_analysis.md       # Market analysis + competitor table
│   └── ux_spec.md               # UX specification + user flows
│
├── reports/
│   └── qa_report.json           # QA report: 226 tests, 99.1% pass rate
│
├── pyproject.toml               # uv workspace root
├── package.json                 # pnpm workspace root
├── Makefile                     # make install / dev / test / lint / build / migrate
└── .github/workflows/
    ├── ci.yml                   # 5 parallel jobs: lint, type-check, unit, integration, docker
    └── release.yml              # Docker build + PyPI publish on git tags
```

---

## Contribution Guidelines

### Branching

| Branch pattern | Purpose |
|---|---|
| `main` | Stable, always deployable. Protected — no direct pushes. |
| `feat/<description>` | New features |
| `fix/<description>` | Bug fixes |
| `chore/<description>` | Tooling, deps, CI |
| `docs/<description>` | Documentation only |
| `apf/<run-id>/<slug>` | APF-generated branches (created by the pipeline itself) |

### Adding a New Agent

1. Add a new artifact model to `packages/agent-core/apf_agent_core/artifacts.py`
2. Add a Jinja2 prompt template to `packages/agent-core/apf_agent_core/prompts/<name>.j2`
3. Implement the agent in `services/agent-runner/apf_agent_runner/agents/<name>.py` extending `BaseAgent`
4. Register the stage in `services/orchestrator/apf_orchestrator/core/dag.py` (`STAGE_DEPS` dict)
5. Write tests in `services/agent-runner/tests/unit/test_agents.py`

### Adding a New Connector

1. Copy `services/slack-connector/` as a template
2. Implement `config.py` (Pydantic Settings), `client.py` (HTTP client), `main.py` (FastAPI app)
3. Add a `Dockerfile` and a Docker Compose service + profile in `deploy/docker-compose.yml`
4. Add the connector type to `CONNECTOR_TYPES` in `services/orchestrator/apf_orchestrator/api/connectors.py`
5. Write tests in `tests/`

### Commit Format

APF uses [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(orchestrator): add configurable HITL gate per stage
fix(agent-runner): handle empty LLM response in structured_output
chore(deps): bump anthropic SDK to 0.29.0
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`

### Code Style

- **Python:** `ruff format` (line length 100) + `ruff check` + `mypy strict`
- **TypeScript:** `eslint` + `prettier`, strict TypeScript, functional components only
- **No hardcoded secrets** anywhere — all credentials via env vars / Pydantic Settings

---

## FAQ

**Q: Can I run APF without Docker?**
Yes. Install dependencies with `uv sync --all-packages --dev`, start Redis locally (`redis-server`), and run each service with `uvicorn`. Use `sqlite+aiosqlite:///./apf.db` as the database URL — no PostgreSQL needed for development.

**Q: Which LLM provider gives the best results?**
`claude-opus-4-6` produces the highest-quality artifacts across all stages. `claude-sonnet-4-6` is a good balance of quality and speed/cost. OpenAI `gpt-4o` also works well for all stages.

**Q: Can I run APF on an air-gapped machine?**
Yes. Set `LLM_PROVIDER=litellm` and point `LITELLM_BASE_URL` at a local Ollama instance. All other services (orchestrator, artifact-store, Redis, PostgreSQL) are self-contained in Docker.

**Q: How do I use APF on an existing codebase?**
Set `GITHUB_DEFAULT_REPO=yourorg/yourrepo` and APF will create branches and PRs against that repo. You can also pass `--repo` to `apf run` per-pipeline.

**Q: What happens if an agent fails?**
The orchestrator retries the failing agent up to 3 times with exponential backoff. If all retries fail, the stage is marked `failed`, the pipeline halts, and you can resume from that stage after fixing the underlying issue (e.g., bad API key, rate limit).

**Q: Can I run just one stage?**
Yes: `apf run --stage prd "my idea"` runs only the PRD agent and returns the artifact.

**Q: How are costs calculated?**
APF makes one LLM call per stage per pipeline run. With `claude-opus-4-6`, a full 11-stage pipeline costs approximately $0.40–$1.20 in API credits depending on the complexity of the idea and the length of prior-stage context injected.

**Q: Is my code / idea sent to the LLM provider?**
Yes — your idea and all intermediate artifacts are sent to the LLM provider of your choice. For confidential ideas, use a self-hosted model via LiteLLM.

**Q: Can multiple users share one APF instance?**
Yes. The orchestrator has multi-user JWT authentication. Each user can see and manage only their own pipelines (unless they have the `admin` role).

---

## License

Copyright 2026 APF Contributors.

Licensed under the [Apache License, Version 2.0](LICENSE).

```
http://www.apache.org/licenses/LICENSE-2.0
```

You may use APF freely for personal, commercial, and internal enterprise use. You may not sublicense or sell APF as a standalone hosted product without modification.
