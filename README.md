# Autonomous Product Factory (APF)

[![CI](https://github.com/DevelopmentLife/autonomous-product-factory/actions/workflows/ci.yml/badge.svg)](https://github.com/DevelopmentLife/autonomous-product-factory/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![React 18](https://img.shields.io/badge/react-18-blue.svg)](https://react.dev)
[![Tests](https://img.shields.io/badge/tests-226%20passing-brightgreen.svg)](#tests)

> **Give it an idea. Get back a pull request.**

APF transforms a plain-English product idea into a merge-ready GitHub pull request — complete with PRD, architecture, market analysis, UX spec, engineering plan, working code, tests, and CI/CD config — in a single command.

```bash
apf run "build a REST API for a subscription billing service"
```

**Nothing is required up front.** Run it locally without any API keys using mock mode, add an LLM key when you want real output, and add GitHub/Slack credentials only when you're ready to wire those in.

---

## Quick Start

### 1. Clone

```bash
git clone https://github.com/DevelopmentLife/autonomous-product-factory.git
cd autonomous-product-factory
```

### 2. Start (zero config required)

```bash
make dev-mock
```

That's it. The full stack starts — orchestrator, agent-runner, artifact-store, dashboard, Redis — using SQLite for storage and a mock LLM that returns realistic placeholder artifacts. No Postgres, no MinIO, no API keys.

- **Dashboard:** http://localhost:3000 (login: `admin` / `changeme`)
- **API:** http://localhost:8000/docs

### 3. Add a real LLM key when ready

Create `deploy/.env` (or copy from the example):

```bash
cp deploy/.env.example deploy/.env
```

Edit it — the only two lines you need to change for real output:

```env
ANTHROPIC_API_KEY=sk-ant-...
APF_ADMIN_PASSWORD=yourpassword
```

Then restart:

```bash
make dev-local
```

### 4. Install the CLI

```bash
pip install ./cli
apf auth login
apf run "build a task management API"
```

---

## All Start Modes

| Command | What it does |
|---|---|
| `make dev-mock` | Full stack, zero config — mock LLM, SQLite, local files |
| `make dev-local` | Full stack with your API key — SQLite, local files, no Postgres/MinIO |
| `make dev` | Full production-like stack — Postgres, MinIO, hot-reload |
| `make dev-local-d` | Same as `dev-local` but detached (runs in background) |
| `make down` | Stop all containers |
| `make logs-local` | Tail logs from the local stack |

---

## Deploy to AWS

APF deploys to AWS ECS Fargate with a single command. The first deploy creates the full infrastructure (VPC, ALB, ECS cluster, RDS PostgreSQL, ElastiCache Redis, EFS for artifacts) via CloudFormation. Subsequent deploys just rebuild and push images.

### Prerequisites

- AWS CLI v2 configured (`aws configure`)
- Docker running
- IAM permissions: ECR, ECS, CloudFormation, IAM, ELB, VPC, SSM, RDS, ElastiCache

### One-time setup: store your secrets in SSM

```bash
# See what commands to run:
make aws-params

# Run them — only APF_SECRET_KEY and APF_ADMIN_PASSWORD are required.
# Everything else (LLM keys, GitHub, Slack) can be empty strings initially.
aws ssm put-parameter --name /apf/APF_SECRET_KEY \
  --value "$(openssl rand -hex 32)" --type SecureString

aws ssm put-parameter --name /apf/APF_ADMIN_PASSWORD \
  --value "yourpassword" --type SecureString

# Add your LLM key (or leave blank to run in mock mode on AWS too)
aws ssm put-parameter --name /apf/ANTHROPIC_API_KEY \
  --value "sk-ant-..." --type SecureString

# Optional — add empty strings for optional connectors now, update later
aws ssm put-parameter --name /apf/GITHUB_APP_ID --value "" --type SecureString
aws ssm put-parameter --name /apf/GITHUB_APP_PRIVATE_KEY --value "" --type SecureString
aws ssm put-parameter --name /apf/GITHUB_WEBHOOK_SECRET --value "" --type SecureString
aws ssm put-parameter --name /apf/GITHUB_DEFAULT_REPO --value "" --type SecureString
aws ssm put-parameter --name /apf/SLACK_BOT_TOKEN --value "" --type SecureString
aws ssm put-parameter --name /apf/SLACK_SIGNING_SECRET --value "" --type SecureString
aws ssm put-parameter --name /apf/OPENAI_API_KEY --value "" --type SecureString
```

### Deploy

```bash
make deploy-aws
# Override region or stack name:
make deploy-aws AWS_REGION=us-west-2 AWS_STACK=apf-staging
```

The script:
1. Creates ECR repos (idempotent)
2. Builds and pushes Docker images for all services
3. Deploys the CloudFormation stack (VPC, ALB, RDS, Redis, EFS, ECS)
4. Forces ECS task redeployment

When complete, the ALB DNS name is printed:
```
LoadBalancerDNS | http://apf-alb-1234567890.us-east-1.elb.amazonaws.com
```

### Update after code changes

```bash
make update-aws   # Rebuilds images + forces ECS redeployment. Skips CloudFormation.
```

### Tear down

```bash
make teardown-aws   # Prompts for confirmation. RDS is snapshotted before deletion.
```

### Costs

A minimal AWS deployment (single AZ, smallest instances) runs approximately **$50–80/month**:
- ECS Fargate tasks: ~$20/month
- RDS `db.t4g.micro`: ~$15/month
- ElastiCache `cache.t4g.micro`: ~$12/month
- ALB: ~$18/month
- NAT Gateway, EFS, data transfer: ~$10/month

---

## How It Works — The 11-Stage Pipeline

APF orchestrates eleven specialist agents in a DAG. Each agent receives the full context from all prior stages before generating its output.

```
Idea
 │
 ├─ Stage 1: PRD Agent         → executive summary, features, success metrics
 ├─ Stage 2: Architect Agent   → system design, data model, API contracts, ADRs
 ├─ Stage 3: Market Agent      → competitor table, positioning, pricing model
 ├─ Stage 4: UX Agent          → user flows, wireframe descriptions, components
 ├─ Stage 5: Engineering Agent → 20-week milestone plan, team sizing, risk register
 ├─ Stage 6: Developer Agent   → working source code + unit tests
 ├─ Stage 7: QA Agent          → test plan, coverage targets, test cases
 ├─ Stage 8: Regression Agent  → regression matrix, edge cases, load scenarios
 ├─ Stage 9: Review Agent      → security audit, code review, approval verdict
 ├─ Stage 10: DevOps Agent     → Dockerfile, GitHub Actions CI, deploy scripts
 └─ Stage 11: README Agent     → full public README for the generated project
        │
        └─ GitHub PR (if GitHub credentials are configured)
```

Stages run as a DAG — independent stages run in parallel. The Review agent can block PR creation and re-trigger the Developer agent if it finds critical issues.

---

## Configuration

All configuration is via environment variables in `deploy/.env`. Copy from `.env.example` and fill in only what you need.

### What's required

| Variable | Default | Notes |
|---|---|---|
| `APF_SECRET_KEY` | — | JWT signing key. Generate: `openssl rand -hex 32` |
| `APF_ADMIN_PASSWORD` | `changeme` | Dashboard login password |

### LLM provider (pick one, or use mock)

| Variable | Default | Notes |
|---|---|---|
| `MOCK_LLM` | `false` | `true` = full pipeline with zero API calls |
| `LLM_PROVIDER` | `anthropic` | `anthropic`, `openai`, or `litellm` |
| `LLM_MODEL` | `claude-opus-4-6` | Any model the provider supports |
| `ANTHROPIC_API_KEY` | — | Required when `LLM_PROVIDER=anthropic` |
| `OPENAI_API_KEY` | — | Required when `LLM_PROVIDER=openai` |
| `LITELLM_BASE_URL` | — | Required when `LLM_PROVIDER=litellm` (e.g., Ollama) |

### Optional connectors

All of these are disabled if the env var is blank — nothing crashes, the feature just doesn't activate.

| Feature | Variable(s) | What it enables |
|---|---|---|
| GitHub PR creation | `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, `GITHUB_DEFAULT_REPO` | Pipeline creates a branch and opens a PR |
| Slack notifications | `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET` | Stage updates + pipeline complete messages |
| Slack HITL gates | above + `SLACK_CHANNEL` | Interactive Approve/Reject buttons |
| AWS deployment | `AWS_ECS_CLUSTER`, `AWS_ECS_SERVICE`, `AWS_ACCESS_KEY_ID` | DevOps agent triggers ECS rolling deploy |
| Jira tickets | `JIRA_URL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY` | Auto-creates Jira issues per stage |
| Confluence pages | `CONFLUENCE_URL`, `CONFLUENCE_API_TOKEN`, `CONFLUENCE_SPACE_KEY` | Publishes artifacts as Confluence pages |

To start optional Docker services (Slack, Jira, Confluence), add their profile:

```bash
# Slack only
docker compose -f deploy/docker-compose.local.yml --profile slack up

# Slack + Jira + Confluence
docker compose -f deploy/docker-compose.local.yml --profile slack --profile jira --profile confluence up
```

---

## The Dashboard

The web dashboard at http://localhost:3000 gives you a real-time view of all pipeline activity.

- **Pipelines list** — all runs with status badges, auto-refreshes every 5s
- **New Pipeline** — type your idea and click Run directly in the browser
- **Pipeline detail** — stage timeline with live WebSocket updates (no page refresh)
- **Pause / Resume / Cancel** — control any running pipeline
- **Integrations page** — shows which connectors are configured

---

## CLI Reference

```bash
pip install ./cli
```

```bash
# Start a pipeline
apf run "build a metrics dashboard"

# Watch live output
apf run "build a rate-limiter" --watch

# Run with no API key (mock mode)
MOCK_LLM=true apf run "build a search service"

# Check status
apf status
apf status <PIPELINE_ID> --watch

# Download artifacts
apf artifacts <PIPELINE_ID> --output ./artifacts/

# Stream logs
apf logs <PIPELINE_ID> --follow

# Manage integrations
apf integrations list
apf integrations enable slack
apf integrations enable github
```

---

## Architecture

```
 CLI / Browser / GitHub Webhooks
          │
          ▼
    orchestrator :8000          — DAG engine, JWT auth, REST + WebSocket API
          │
    ┌─────┴──────┐
    │            │
agent-runner   artifact-store :8001   — ECS workers / local process
    │
   LLM (Anthropic / OpenAI / LiteLLM / Mock)
          │
    Redis Streams                     — event bus between services
          │
    ┌──────────────────────────┐
    │       Connectors         │
    │  github-integration      │  — optional, profile: (core)
    │  slack-connector         │  — optional, profile: slack
    │  jira-connector          │  — optional, profile: jira
    │  confluence-connector    │  — optional, profile: confluence
    │  aws-connector           │  — optional, profile: aws
    └──────────────────────────┘
          │
    Storage
    SQLite (local) / PostgreSQL (prod)
    Local filesystem / EFS (AWS)
```

All backend services: Python 3.12 + FastAPI. Dashboard: React 18 + Vite + TypeScript + Tailwind. Package manager: `uv` (Python), `pnpm` (Node).

---

## Project Structure

```
autonomous-product-factory/
├── packages/
│   ├── agent-core/       # BaseAgent, 11 artifact models, LLM provider abstraction
│   ├── db/               # SQLAlchemy 2.x models + Alembic migrations
│   └── event-bus/        # Redis Streams client + InMemoryEventBus test stub
├── services/
│   ├── orchestrator/     # Core: DAG engine, auth, REST + WebSocket API
│   ├── agent-runner/     # 11 agent implementations + SAST secret scanner
│   ├── artifact-store/   # Versioned artifact storage (local FS or S3)
│   ├── github-integration/
│   ├── slack-connector/
│   ├── jira-connector/
│   ├── confluence-connector/
│   ├── aws-connector/
│   └── dashboard/        # React 18 web UI
├── cli/                  # apf CLI (Click)
├── deploy/
│   ├── docker-compose.local.yml  # Lightweight local dev (SQLite, no Postgres/MinIO)
│   ├── docker-compose.yml        # Full stack (Postgres, MinIO, all services)
│   ├── docker-compose.dev.yml    # Dev override (hot-reload, volume mounts)
│   ├── .env.example              # All variables documented
│   └── aws/
│       ├── deploy.sh             # Build, push to ECR, deploy CloudFormation
│       ├── cloudformation.yml    # Full ECS Fargate + RDS + Redis + EFS stack
│       └── teardown.sh           # Destroy the AWS stack
└── docs/                 # PRD, architecture, engineering plan, market analysis, UX spec
```

---

## Tests

```bash
# Run all tests
make test-python

# Per-service
cd services/orchestrator && python -m pytest tests/ -q
cd services/agent-runner && python -m pytest tests/ -q
```

| Suite | Tests | Status |
|---|---|---|
| packages/agent-core | 118 | PASS |
| packages/event-bus | 8 (96% coverage) | PASS |
| services/orchestrator | 28 | PASS |
| services/artifact-store | 41 | PASS |
| services/agent-runner | 10 | PASS |
| services/slack-connector | 6 | PASS |
| services/jira-connector | 4 | PASS |
| services/confluence-connector | 3 | PASS |
| services/aws-connector | 4 | PASS |
| **Total** | **226** | **PASS** |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

Conventional Commits: `feat(orchestrator): ...`, `fix(agent-runner): ...`, `chore(deps): ...`

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
