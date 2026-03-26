# Autonomous Product Factory (APF)

[![CI](https://github.com/apf-project/apf/actions/workflows/ci.yml/badge.svg)](https://github.com/apf-project/apf/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/apf-project/apf/branch/main/graph/badge.svg)](https://codecov.io/gh/apf-project/apf)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/apf-cli)](https://pypi.org/project/apf-cli/)
[![Docker](https://img.shields.io/badge/ghcr.io-apf--project-blue)](https://github.com/orgs/apf-project/packages)

**APF transforms a raw product idea — expressed in plain English — into a merge-ready GitHub pull request, complete with a PRD, architecture document, implementation, tests, CI/CD configuration, and documentation, in under 15 minutes.**

A self-hosted, multi-agent pipeline orchestrates eleven specialized AI agents through every stage of the software development lifecycle: requirements, architecture, market analysis, UX specification, engineering planning, implementation, QA, regression testing, peer review, DevOps packaging, and README generation. Optional bots for Slack, Jira, Confluence, and AWS connect APF to your existing toolchain without affecting core pipeline execution.

---

## Table of Contents

1. [Architecture Summary](#architecture-summary)
2. [Service Map](#service-map)
3. [Setup Instructions](#setup-instructions)
4. [Test Instructions](#test-instructions)
5. [CLI Reference](#cli-reference)
6. [Contribution Guidelines](#contribution-guidelines)
7. [License](#license)

---

## Architecture Summary

APF is a polyglot microservices system. All backend services are written in **Python 3.12 + FastAPI**; the web dashboard is **React 18 + TypeScript + Vite**. Services communicate internally over **Redis Streams** (event bus) and expose health/metrics endpoints for observability. Artifacts are stored in **MinIO** (self-hosted) or **AWS S3** (production). The persistence layer uses **SQLite** by default for zero-dependency local development, and **PostgreSQL 15** for production.

```
                       ┌──────────────────────────────────────────────────────────────┐
                       │                         APF Platform                          │
                       │                                                                │
 ┌──────────┐          │  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐  │
 │  CLI     │─────────▶│  │ orchestrator│───▶│  agent-runner│───▶│  artifact-store  │  │
 └──────────┘          │  │  :8000      │    │  (worker)    │    │  :8001           │  │
                       │  └──────┬──────┘    └──────────────┘    └──────────────────┘  │
 ┌──────────┐          │         │                                                      │
 │ Browser  │─────────▶│  ┌──────▼──────┐                                              │
 └──────────┘          │  │dashboard-ui │    ┌──────────────────────────────────────┐  │
                       │  │  :3000      │    │          Event Bus (Redis Streams)    │  │
 ┌──────────┐          │  └─────────────┘    │  apf:stage:dispatch                  │  │
 │  GitHub  │─────────▶│                     │  apf:stage:result / apf:stage:log    │  │
 │ Webhooks │          │                     │  apf:pipeline:status / :approval     │  │
 └──────────┘          │                     │  apf:connector:action                │  │
                       │                     └──────────────────────────────────────┘  │
 ┌──────────┐          │                                                                │
 │  Slack   │─────────▶│  ┌─────────────────────────────────────────────────────────┐  │
 └──────────┘          │  │                     Connectors                           │  │
                       │  │  github-integration  slack-connector  jira-connector     │  │
                       │  │  confluence-connector               aws-connector        │  │
                       │  └─────────────────────────────────────────────────────────┘  │
                       │                                                                │
                       │  ┌─────────────────────────────────────────────────────────┐  │
                       │  │  PostgreSQL / SQLite     Redis 7     MinIO / S3          │  │
                       │  └─────────────────────────────────────────────────────────┘  │
                       └──────────────────────────────────────────────────────────────┘
```

**Key design decisions:**

- **Microservices** — connectors are independently deployable and can be omitted entirely from Docker Compose when not needed.
- **Redis Streams as event bus** — Redis is already required as a cache; Streams provide at-least-once delivery without adding a second broker.
- **SQLite / PostgreSQL dual support** — the same SQLAlchemy 2.x ORM code targets both; switching requires only a connection string change and `alembic upgrade head`.
- **MinIO / S3 unified artifact store** — a single S3-compatible code path; MinIO runs as a sidecar in self-hosted mode and real S3 is used in production.
- **Python for all backend services** — the LLM ecosystem (Anthropic SDK, OpenAI SDK, LangChain, Semgrep) is Python-first; FastAPI provides async-native HTTP and automatic OpenAPI generation.

---

## Service Map

| Service | Port | Language | Responsibility |
|---|---|---|---|
| `orchestrator` | 8000 | Python / FastAPI | Core pipeline runtime: DAG execution, stage dispatch, retries, checkpoints, quality gates, REST + WebSocket API |
| `agent-runner` | — (worker) | Python / FastAPI | Executes individual agent stages: LLM prompt construction, streaming calls, artifact validation, SAST |
| `artifact-store` | 8001 | Python / FastAPI | Stores, versions, and serves all pipeline artifacts; S3-compatible backend abstraction |
| `dashboard-ui` | 3000 | TypeScript / React 18 | Web dashboard: pipeline list, DAG visualization, live log viewer, artifact viewer, settings |
| `github-integration` | 8002 | Python / FastAPI | GitHub App webhooks, branch creation, multi-file commits, PR creation, review comment posting |
| `slack-connector` | 8003 | Python / FastAPI | Pipeline notifications, slash commands (`/apf`), interactive HITL approval buttons |
| `jira-connector` | 8004 | Python / FastAPI | Epic / Story / Task creation, status transitions, PR remote links, artifact attachments |
| `confluence-connector` | 8005 | Python / FastAPI | Markdown → Confluence Storage Format conversion, page upsert with version history |
| `aws-connector` | 8006 | Python / FastAPI | CodePipeline trigger, ECS rolling deploy, Lambda update, Terraform plan/apply, deployment polling |
| `PostgreSQL` | 5432 | — | Primary relational store (pipelines, stages, artifacts, agent runs, connector configs, audit log) |
| `Redis` | 6379 | — | Event bus (Streams), cache, session store, WebSocket pub/sub |
| `MinIO` | 9000 / 9001 | — | S3-compatible artifact blob storage (self-hosted deployments) |

---

## Setup Instructions

### Prerequisites

| Requirement | Minimum Version | Notes |
|---|---|---|
| Docker | 26.x | Required for `docker compose` |
| Docker Compose | v2 (plugin) | `docker compose` (not `docker-compose`) |
| Python | 3.11+ | Only needed if installing the CLI locally |
| `uv` | 0.4.x | Python package manager (optional; used by dev setup script) |
| Git | 2.x | For cloning and branch operations |
| An LLM API key | — | Anthropic (recommended) or OpenAI |

For local development without Docker, also install:

```bash
# Python toolchain
pip install uv
uv sync --all-packages --dev

# Node.js toolchain (for dashboard development only)
corepack enable
pnpm install --frozen-lockfile
```

### One-Command Start

```bash
git clone https://github.com/apf-project/apf.git
cd apf
cp deploy/.env.example deploy/.env   # Fill in your API keys (see table below)
docker compose -f deploy/docker-compose.yml up
```

The dashboard will be available at `http://localhost:3000`.
The orchestrator API will be available at `http://localhost:8000/api/v1`.

To include optional connectors, add their service names to the compose command:

```bash
docker compose -f deploy/docker-compose.yml \
  --profile slack --profile jira \
  up
```

### Environment Variable Reference

All variables are set in `deploy/.env` (or exported in the shell / injected via CI secrets). Sensitive values are never stored in config files.

#### Core

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | No | SQLite at `~/.apf/apf.db` | PostgreSQL: `postgresql+asyncpg://user:pass@host/apf` |
| `REDIS_URL` | No | `redis://localhost:6379` | Redis connection string |
| `ARTIFACT_STORE_BACKEND` | No | `local` | `local` or `s3` |
| `ARTIFACT_STORE_PATH` | No | `~/.apf/artifacts` | Local filesystem path (when `BACKEND=local`) |
| `ARTIFACT_STORE_ENDPOINT` | No | `http://minio:9000` | S3-compatible endpoint (when `BACKEND=s3`) |
| `ARTIFACT_STORE_BUCKET` | No | `apf-artifacts` | S3 / MinIO bucket name |
| `AWS_ACCESS_KEY_ID` | Cond. | — | Required when `BACKEND=s3` |
| `AWS_SECRET_ACCESS_KEY` | Cond. | — | Required when `BACKEND=s3` |
| `APF_SECRET_KEY` | Yes | — | Random secret for JWT signing (`openssl rand -hex 32`) |
| `APF_ADMIN_USERNAME` | No | `admin` | Initial admin user username |
| `APF_ADMIN_PASSWORD` | Yes | — | Initial admin user password |
| `MAX_CONCURRENT_PIPELINES` | No | `5` | Semaphore cap for simultaneous pipeline runs |
| `PIPELINE_RETENTION_DAYS` | No | `90` | Days before pipeline records are purged |

#### LLM Provider

| Variable | Required | Default | Description |
|---|---|---|---|
| `LLM_PROVIDER` | Yes | `anthropic` | `anthropic`, `openai`, or `litellm` |
| `LLM_MODEL` | No | `claude-3-5-sonnet-20241022` | Model identifier for the selected provider |
| `ANTHROPIC_API_KEY` | Cond. | — | Required when `LLM_PROVIDER=anthropic` |
| `OPENAI_API_KEY` | Cond. | — | Required when `LLM_PROVIDER=openai` |
| `LITELLM_BASE_URL` | Cond. | — | Required when `LLM_PROVIDER=litellm` (e.g., Ollama endpoint) |
| `LLM_MAX_TOKENS` | No | `8192` | Max output tokens per agent call |
| `LLM_TEMPERATURE` | No | `0.3` | Sampling temperature |

#### Connector: Slack

| Variable | Required | Description |
|---|---|---|
| `SLACK_BOT_TOKEN` | Yes | Slack Bot User OAuth token (`xoxb-...`) |
| `SLACK_SIGNING_SECRET` | Yes | Slack app signing secret for webhook validation |
| `SLACK_NOTIFICATION_CHANNEL` | Yes | Default channel for pipeline notifications (e.g., `#apf-pipelines`) |
| `SLACK_APPROVAL_TIMEOUT_SECONDS` | No (default: `3600`) | Seconds before an unanswered HITL gate auto-cancels |

#### Connector: Jira

| Variable | Required | Description |
|---|---|---|
| `JIRA_BASE_URL` | Yes | e.g., `https://yourorg.atlassian.net` |
| `JIRA_API_TOKEN` | Yes | Jira Cloud / Server API token |
| `JIRA_USER_EMAIL` | Yes | Email of the service account associated with the API token |
| `JIRA_PROJECT_KEY` | Yes | Target Jira project key (e.g., `ENG`) |
| `JIRA_EPIC_ISSUE_TYPE` | No (default: `Epic`) | Issue type name for pipeline-level epics |

#### Connector: Confluence

| Variable | Required | Description |
|---|---|---|
| `CONFLUENCE_BASE_URL` | Yes | e.g., `https://yourorg.atlassian.net/wiki` |
| `CONFLUENCE_API_TOKEN` | Yes | Confluence Cloud / Server API token |
| `CONFLUENCE_USER_EMAIL` | Yes | Email of the service account |
| `CONFLUENCE_SPACE_KEY` | Yes | Target Confluence space key (e.g., `DOCS`) |
| `CONFLUENCE_PARENT_PAGE_ID` | Yes | Numeric ID of the parent page for APF-published pages |

#### Connector: GitHub

| Variable | Required | Description |
|---|---|---|
| `GITHUB_APP_ID` | Yes | GitHub App ID |
| `GITHUB_APP_PRIVATE_KEY` | Yes | PEM-encoded GitHub App private key (newlines as `\n`) |
| `GITHUB_APP_INSTALLATION_ID` | Yes | Installation ID for the target organization or repository |
| `GITHUB_WEBHOOK_SECRET` | Yes | Shared secret for HMAC-SHA256 webhook validation |
| `GITHUB_DEFAULT_REPO` | Yes | Default target repository (`owner/repo`) |
| `GITHUB_DEFAULT_BASE_BRANCH` | No (default: `main`) | Base branch for APF-generated pull requests |

#### Connector: AWS

| Variable | Required | Description |
|---|---|---|
| `AWS_REGION` | Yes | AWS region (e.g., `us-east-1`) |
| `AWS_ROLE_ARN` | Cond. | IAM role ARN for deployment (if using role assumption) |
| `AWS_DEPLOYMENT_TARGET` | Yes | `codepipeline`, `ecs`, or `lambda` |
| `AWS_DEPLOYMENT_TARGET_NAME` | Yes | Pipeline name, ECS cluster/service, or Lambda function name |

### Initial Configuration Wizard

For interactive setup, run the CLI configuration wizard after starting the stack:

```bash
pip install apf-cli
apf config init
```

The wizard prompts for LLM provider, GitHub integration, artifact storage backend, and optional connectors, then writes `.apf/config.yaml`.

---

## Test Instructions

### Prerequisites for Running Tests

```bash
# Install all Python dependencies (including dev/test extras)
uv sync --all-packages --dev

# Install Node.js dependencies (for dashboard tests)
pnpm install --frozen-lockfile
```

### Unit Tests

```bash
# Run all Python unit tests (excludes integration and e2e)
uv run pytest packages/ services/ cli/ \
  -m "not integration and not e2e" \
  --cov=. \
  --cov-report=term-missing \
  --cov-fail-under=80 \
  -n auto

# Run TypeScript unit tests (dashboard)
pnpm --filter dashboard run test

# Run TypeScript tests with coverage
pnpm --filter dashboard run test --coverage
```

### Integration Tests

Integration tests require live Redis and PostgreSQL instances. The easiest way to provide them is via Docker Compose:

```bash
docker compose -f deploy/docker-compose.yml up -d redis postgres

# Apply database migrations
uv run alembic -c packages/db/alembic.ini upgrade head

# Run integration tests
uv run pytest services/ packages/ \
  -m "integration" \
  --timeout=120 \
  -x
```

Required environment variables for integration tests:

```bash
export DATABASE_URL=postgresql+asyncpg://postgres:test@localhost/apf_test
export REDIS_URL=redis://localhost:6379
```

### Contract Tests

Contract tests verify API shape compatibility between the CLI (consumer) and the orchestrator (provider) using `pact-python`, and fuzz all endpoints using `schemathesis`.

```bash
# Pact consumer-driven contracts
uv run pytest cli/tests/pacts/ services/orchestrator/tests/contract/ -m "contract"

# OpenAPI fuzz testing (requires a running orchestrator)
docker compose -f deploy/docker-compose.yml up -d orchestrator redis
uv run schemathesis run http://localhost:8000/api/v1/openapi.json --checks all
```

### End-to-End Tests

E2E tests use Playwright against a fully composed local environment.

```bash
# Install Playwright browsers (first time only)
pnpm --filter dashboard exec playwright install --with-deps

# Start the full stack
docker compose -f deploy/docker-compose.yml up -d

# Run E2E tests
pnpm --filter dashboard run test:e2e
```

Key E2E scenarios covered:
- Full pipeline run via dashboard (idea → PR URL visible in UI)
- Full pipeline run via CLI
- Pipeline failure and retry
- Slack HITL approval gate
- Resume from checkpoint (`--from <stage>`)
- Artifact ZIP download

### Coverage Report

```bash
# Generate an HTML coverage report
uv run pytest packages/ services/ cli/ \
  -m "not integration and not e2e" \
  --cov=. \
  --cov-report=html:htmlcov

open htmlcov/index.html
```

Minimum enforced coverage thresholds:

| Package / Service | Threshold |
|---|---|
| `packages/agent-core` | 90% |
| `packages/event-bus` | 90% |
| `services/orchestrator` core | 90% |
| `services/artifact-store` | 90% |
| `services/orchestrator` API | 85% |
| `services/agent-runner` | 85% |
| `services/github-integration` | 85% |
| `packages/db` | 85% |
| `cli/` | 80% |
| `services/slack-connector` | 80% |
| `services/jira-connector` | 80% |
| `services/confluence-connector` | 80% |
| `services/aws-connector` | 75% |

---

## CLI Reference

Install the CLI:

```bash
pip install apf-cli
# or from source:
uv tool install ./cli
```

Authenticate:

```bash
apf auth login                        # Browser OAuth flow
apf auth login --token $APF_TOKEN     # Non-interactive (CI)
apf auth whoami                       # Show current user
apf auth logout
```

### `apf run` — Trigger a Pipeline

```bash
# Run a full 11-stage pipeline
apf run "build a REST API for a bookstore"

# Run a single agent stage in isolation
apf run --stage prd "build a task management app"

# Resume a previous run from a specific stage
apf run --from architect --resume-run-id <RUN_ID>

# Use a specific config file
apf run --config /path/to/.apf/config.yaml "build an auth service"

# Machine-readable output for CI scripts
apf run --json "build a metrics dashboard"

# Suppress all output except errors and final result
apf run --quiet "build a webhook processor"
```

### `apf status` — Check Pipeline Status

```bash
# Show status of all recent pipeline runs
apf status

# Show status of a specific run
apf status <RUN_ID>

# Poll status until the pipeline finishes
apf status <RUN_ID> --watch

# Machine-readable status
apf status <RUN_ID> --json
```

Example output:

```
[APF] Pipeline run-abc123
  Status:   running
  Stage:    developer (6/11)
  Started:  2026-03-23 14:02:11 UTC  (3m 14s ago)
  PR:       —
```

### `apf logs` — Stream Agent Logs

```bash
# Stream live logs for a running pipeline
apf logs <RUN_ID> --follow

# Retrieve logs for a specific stage
apf logs <RUN_ID> --stage prd

# Filter by log level
apf logs <RUN_ID> --stage developer --level error
```

### `apf artifacts` — List and Download Artifacts

```bash
# List all artifacts produced by a run
apf artifacts <RUN_ID>

# Download artifacts for a specific stage to a local directory
apf artifacts <RUN_ID> --stage architect --output ./out/

# Download all artifacts for a run
apf artifacts <RUN_ID> --output ./out/
```

### `apf config` — Configuration Management

```bash
# Launch interactive setup wizard
apf config init

# Create global config (stored at ~/.apf/config.yaml)
apf config init --global

# Validate current configuration
apf config validate

# Validate a specific config file
apf config validate --config /path/to/.apf/config.yaml
```

### `apf integrations` — Connector Management

```bash
# List all integrations and their connection status
apf integrations list

# Enable a connector (prompts for required configuration)
apf integrations enable slack
apf integrations enable jira
apf integrations enable confluence
apf integrations enable aws

# Enable with inline configuration
apf integrations enable slack --config SLACK_BOT_TOKEN=xoxb-... --config SLACK_SIGNING_SECRET=...

# Disable a connector (does not delete stored config)
apf integrations disable aws
```

### Output Format

Default output uses the Rich terminal renderer with real-time stage progress:

```
[APF] Starting pipeline run-abc123
[PRD        ] Running...
[PRD        ] Completed in 12.3s
[ARCHITECT  ] Running...
[ARCHITECT  ] Completed in 18.7s
...
[README     ] Completed in 8.1s
[APF] Pipeline completed in 8m 42s
      PR:  https://github.com/owner/repo/pull/47
      Dashboard: http://localhost:3000/pipelines/run-abc123
```

With `--json`, each event is emitted as a newline-delimited JSON object:

```json
{"event": "stage_completed", "run_id": "run-abc123", "stage": "prd", "duration_ms": 12340, "status": "completed"}
```

---

## Contribution Guidelines

### Branching Strategy

| Branch | Purpose |
|---|---|
| `main` | Stable, always deployable. Protected — direct pushes are blocked. |
| `feat/<short-description>` | New features or agents |
| `fix/<short-description>` | Bug fixes |
| `chore/<short-description>` | Dependency updates, tooling, CI changes |
| `docs/<short-description>` | Documentation-only changes |
| `apf/<run-id>/<slug>` | APF-generated branches (created automatically by the pipeline) |

Always branch from `main`. Rebase onto `main` before opening a PR; do not merge `main` into your feature branch.

### Development Setup

```bash
git clone https://github.com/apf-project/apf.git
cd apf

# Install Python workspace (all packages and services)
uv sync --all-packages --dev

# Install pre-commit hooks
uv run pre-commit install

# Install Node.js dependencies (dashboard only)
pnpm install --frozen-lockfile

# Start backing services
docker compose -f deploy/docker-compose.yml up -d redis postgres minio

# Run database migrations
uv run alembic -c packages/db/alembic.ini upgrade head

# Start the orchestrator with hot reload
uv run uvicorn apf_orchestrator.main:app --reload --port 8000

# Start the dashboard dev server
pnpm --filter dashboard run dev
```

### Pull Request Process

1. **Open an issue first** for non-trivial changes to align on approach before investing implementation time.
2. **Branch from `main`** using the naming convention above.
3. **Write tests** — PRs that reduce coverage below the service threshold will not be merged.
4. **Run the full local check** before pushing:
   ```bash
   uv run ruff check .
   uv run ruff format --check .
   uv run mypy packages/ services/ cli/ --ignore-missing-imports
   uv run pytest packages/ services/ cli/ -m "not integration and not e2e" -n auto
   pnpm --filter dashboard run lint
   pnpm --filter dashboard run type-check
   pnpm --filter dashboard run test
   ```
5. **Fill in the PR template** — describe the motivation, what changed, and how to test it.
6. **Request at least one review** from a code owner (see `CODEOWNERS`).
7. **Squash on merge** — the PR title becomes the squash commit message; ensure it is a valid Conventional Commit.

### Commit Format

APF uses [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]

[optional footer: BREAKING CHANGE, Closes #issue]
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`

**Scopes** (optional): `orchestrator`, `agent-runner`, `artifact-store`, `dashboard`, `cli`, `github`, `slack`, `jira`, `confluence`, `aws`, `packages`

Examples:

```
feat(orchestrator): add configurable HITL gate per pipeline stage
fix(agent-runner): handle empty LLM response in structured_output path
chore(deps): bump anthropic SDK to 0.28.0
docs(cli): add --json flag examples to CLI reference
```

### Code Style

**Python:**

- Formatter: `ruff format` (line length 100)
- Linter: `ruff check` (rule set: `E`, `F`, `I`, `N`, `UP`, `B`, `A`, `ANN`)
- Type checker: `mypy` (strict on `packages/`, `services/orchestrator/`, `cli/`)
- Docstrings: Google-style for all public classes and functions
- All async functions must use `async def`; no `asyncio.run()` in library code

**TypeScript (dashboard):**

- Formatter / linter: `eslint` + `prettier` (config in `services/dashboard/.eslintrc`)
- Strict TypeScript: `"strict": true` in `tsconfig.json`
- Components: functional only; no class components
- State: Zustand for global state; TanStack Query for server state; `useState` for local UI state

**General:**

- No hardcoded credentials, tokens, or secrets anywhere in the codebase — use environment variables or the secrets backend.
- All environment-dependent configuration is read through Pydantic `Settings` (`pydantic-settings`) or the `.apf/config.yaml` schema.
- Pre-commit hooks (`ruff`, `mypy`, `prettier`) run automatically on `git commit` and must pass.

### Architecture Decision Records

Non-obvious architectural decisions are documented as ADRs in `docs/adr/`. If your PR makes a significant architectural choice, add an ADR explaining the context, decision, and trade-offs. ADRs are numbered sequentially and are never deleted — superseded ADRs are marked as such.

---

## License

Copyright 2026 APF Project Contributors.

Licensed under the [Apache License, Version 2.0](LICENSE). You may not use this software except in compliance with the License. A copy of the License is included in this repository at `LICENSE`, and is also available at:

```
http://www.apache.org/licenses/LICENSE-2.0
```

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
