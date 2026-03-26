# Engineering Plan: Autonomous Product Factory (APF)

**Version:** 1.0.0
**Status:** Approved for Implementation
**Date:** 2026-03-23
**Authored by:** Engineering Agent
**Inputs:** `prd.md` v1.0.0, `market_analysis.md` 2026-03-23

---

## Table of Contents

1. [Tech Stack Decisions](#1-tech-stack-decisions)
2. [Repository Structure](#2-repository-structure)
3. [Services Build Order](#3-services-build-order)
4. [Service Specifications](#4-service-specifications)
5. [API Contracts](#5-api-contracts)
6. [Event Schemas](#6-event-schemas)
7. [Database Schemas](#7-database-schemas)
8. [Testing Strategy](#8-testing-strategy)
9. [CI/CD Pipeline](#9-cicd-pipeline)
10. [Milestones](#10-milestones)

---

## 1. Tech Stack Decisions

### 1.1 Backend: Python + FastAPI

**Decision:** Python 3.12 + FastAPI 0.111.x

**Rationale:**
- The LLM ecosystem is overwhelmingly Python-first. Anthropic SDK, OpenAI SDK, LangChain, LangGraph, CrewAI, and all mainstream agent frameworks publish Python packages as their primary interface. Using Python eliminates an entire class of FFI friction.
- FastAPI provides async-native HTTP via Starlette/uvicorn, native OpenAPI schema generation (required for contract testing), and Pydantic v2 for artifact schema validation — a direct match for the artifact-validation requirement in the PRD.
- TypeScript/NestJS was considered but rejected because: (a) native LLM SDKs are secondary-class in the Node ecosystem, (b) Pydantic's runtime schema validation outperforms Zod for the structured-output use case, and (c) the agent-runner and orchestrator are CPU/IO-bound async workloads that map cleanly to Python's asyncio.
- Python ships well in Docker; the self-hosted deployment requirement is satisfied equally by both languages.

**Runtime versions:**
- Python 3.12 (minimum 3.11)
- FastAPI 0.111.x
- Uvicorn 0.30.x (ASGI server, with `uvicorn[standard]` for WebSocket support)
- Pydantic 2.7.x

### 1.2 Frontend: React + Vite + TypeScript

**Decision:** React 18 + Vite 5 + TypeScript 5.4 + Tailwind CSS 3.x + shadcn/ui

**Rationale:**
- React 18 concurrent features (Suspense, streaming) align with the real-time dashboard requirement.
- Vite 5 provides sub-second HMR and optimal production bundle splitting.
- shadcn/ui (Radix UI primitives + Tailwind) provides accessible, composable components without a heavy component library dependency — critical for the dashboard's DAG visualization and log viewer.
- Recharts for pipeline metrics; `xterm.js` for the streaming log viewer; `reactflow` for the DAG stage visualization.

### 1.3 Database

**Decision:** SQLite (default, development/single-node) via SQLAlchemy 2.x + Alembic; PostgreSQL 15 (production/HA)

**Rationale:**
- SQLite satisfies the PRD requirement for "single-node deployment with no external dependencies." Zero-config for the solo developer persona.
- SQLAlchemy 2.x async engine supports both SQLite and PostgreSQL with the same ORM code; switching from SQLite to PostgreSQL requires only a connection string change and `alembic upgrade head`.
- Alembic provides versioned, reproducible migrations required for the enterprise upgrade path.
- PostgreSQL 15 is the production target: supports JSONB for artifact metadata, advisory locks for distributed pipeline coordination, and pg_notify for lightweight event propagation.

### 1.4 Message Queue: Redis Streams

**Decision:** Redis 7.x with Redis Streams (via `redis-py` 5.x async client)

**Rationale:**
- Redis Streams provide consumer groups, at-least-once delivery, and message acknowledgement — sufficient for the APF event bus without the operational overhead of Kafka or RabbitMQ.
- Redis is already a common self-hosted dependency (used by many teams for caching); adding it does not introduce a new operational category.
- For minimal installs (solo developer), the orchestrator can run in-process with an asyncio queue as a Redis drop-in; Redis is required only when worker count > 1.
- `redis-py` 5.x supports async/await natively.

### 1.5 LLM Client Library

**Decision:** `anthropic` SDK 0.27.x (primary), `openai` SDK 1.30.x (secondary), custom `LLMProvider` abstraction layer

**Rationale:**
- A thin provider abstraction (`LLMProvider` protocol) is implemented in `packages/agent-core/` so that any agent can be pointed at Claude, GPT-4o, Mistral, or an Ollama-hosted model by changing a config value.
- The abstraction exposes: `complete(messages, model, max_tokens, temperature) -> str`, `stream(messages, ...) -> AsyncIterator[str]`, and `structured_output(messages, schema: type[BaseModel], ...) -> BaseModel`.
- `litellm` 1.40.x is used as the underlying router when the configured provider is not Anthropic or OpenAI directly, enabling Ollama, Mistral, Groq, and any OpenAI-compatible endpoint.

### 1.6 Testing Frameworks

| Layer | Framework | Rationale |
|---|---|---|
| Unit (Python) | `pytest` 8.x + `pytest-asyncio` 0.23.x | Industry standard; async support; parametrize for agent prompt testing |
| Unit (TypeScript) | `vitest` 1.x | Co-located with Vite; 10x faster than Jest for this stack |
| Integration | `pytest` + `httpx` 0.27.x (ASGI test client) | In-process FastAPI testing without spinning up a server |
| Contract | `schemathesis` 3.x (OpenAPI fuzzing) + `pact-python` 2.x | Bidirectional contract testing for API consumers |
| E2E | `playwright` 1.44.x | Browser E2E for dashboard; also used for CLI smoke tests via subprocess |
| Coverage | `coverage.py` 7.x + `pytest-cov` | Line + branch coverage; enforced at 80% minimum |
| Load | `locust` 2.x | Pipeline throughput benchmarks for the orchestrator |

### 1.7 Containerization

**Decision:** Docker (Dockerfile per service) + Docker Compose v2 (single-node deployment) + Helm chart (Kubernetes/enterprise)

- Each service has its own `Dockerfile` using multi-stage builds (builder + slim runtime image).
- Base image: `python:3.12-slim` for backend services; `node:20-alpine` for the frontend build stage with `nginx:1.26-alpine` as the runtime.
- `docker-compose.yml` at repo root composes all services for the self-hosted single-node deployment.
- A `helm/apf/` chart is provided for enterprise Kubernetes deployment.
- Images are published to `ghcr.io/apf-project/` on each tagged release.

---

## 2. Repository Structure

```
apf/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                    # PR checks: lint, test, build
│   │   ├── release.yml               # Tag-triggered: build images, publish, create GitHub release
│   │   └── dependency-review.yml     # Dependabot security review on PRs
│   ├── CODEOWNERS
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.yml
│   │   └── feature_request.yml
│   └── pull_request_template.md
│
├── packages/                         # Shared internal libraries (not deployable on their own)
│   ├── agent-core/                   # Agent base classes, LLM provider abstraction, artifact schemas
│   │   ├── apf_agent_core/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py              # BaseAgent abstract class
│   │   │   ├── artifacts.py          # Pydantic artifact schema definitions (all 11 stages)
│   │   │   ├── context.py            # PipelineContext dataclass
│   │   │   ├── llm/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── provider.py       # LLMProvider Protocol
│   │   │   │   ├── anthropic.py      # AnthropicProvider
│   │   │   │   ├── openai.py         # OpenAIProvider
│   │   │   │   └── litellm.py        # LiteLLMProvider (Ollama, Mistral, etc.)
│   │   │   ├── prompts/              # System prompts per agent (jinja2 templates)
│   │   │   │   ├── prd.j2
│   │   │   │   ├── architect.j2
│   │   │   │   ├── market.j2
│   │   │   │   ├── ux.j2
│   │   │   │   ├── engineering.j2
│   │   │   │   ├── developer.j2
│   │   │   │   ├── qa.j2
│   │   │   │   ├── regression.j2
│   │   │   │   ├── review.j2
│   │   │   │   ├── devops.j2
│   │   │   │   └── readme.j2
│   │   │   └── validators.py         # JSON schema / pydantic validators for artifact outputs
│   │   ├── tests/
│   │   │   ├── test_agent.py
│   │   │   ├── test_artifacts.py
│   │   │   ├── test_llm_provider.py
│   │   │   └── test_validators.py
│   │   ├── pyproject.toml
│   │   └── README.md
│   │
│   ├── db/                           # SQLAlchemy models + Alembic migrations (shared by orchestrator & API)
│   │   ├── apf_db/
│   │   │   ├── __init__.py
│   │   │   ├── models.py             # ORM models: Pipeline, Stage, Artifact, AgentRun, ConnectorConfig, AuditLog
│   │   │   ├── session.py            # Async session factory
│   │   │   └── migrations/           # Alembic env + version scripts
│   │   │       ├── env.py
│   │   │       ├── script.py.mako
│   │   │       └── versions/
│   │   │           └── 0001_initial_schema.py
│   │   ├── tests/
│   │   │   └── test_models.py
│   │   ├── alembic.ini
│   │   └── pyproject.toml
│   │
│   └── event-bus/                    # Redis Streams client wrapper + event schema definitions
│       ├── apf_event_bus/
│       │   ├── __init__.py
│       │   ├── client.py             # EventBusClient (publish/subscribe/ack)
│       │   ├── schemas.py            # Pydantic event schemas for all internal events
│       │   └── streams.py            # Stream name constants
│       ├── tests/
│       │   └── test_event_bus.py
│       └── pyproject.toml
│
├── services/
│   ├── orchestrator/                 # Core pipeline engine + REST API
│   │   ├── apf_orchestrator/
│   │   │   ├── __init__.py
│   │   │   ├── main.py               # FastAPI app factory
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── pipelines.py      # /api/v1/pipelines endpoints
│   │   │   │   ├── stages.py         # /api/v1/stages endpoints
│   │   │   │   ├── artifacts.py      # /api/v1/artifacts endpoints
│   │   │   │   ├── connectors.py     # /api/v1/connectors endpoints
│   │   │   │   ├── auth.py           # /api/v1/auth endpoints
│   │   │   │   ├── health.py         # /healthz, /readyz, /metrics
│   │   │   │   └── websocket.py      # /ws/pipelines/{run_id} live events
│   │   │   ├── core/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── engine.py         # PipelineEngine: DAG execution, stage dispatch
│   │   │   │   ├── scheduler.py      # Concurrent run scheduler (semaphore-based)
│   │   │   │   ├── checkpoint.py     # Stage checkpoint save/restore
│   │   │   │   ├── retry.py          # Exponential backoff retry logic
│   │   │   │   └── dag.py            # DAG definition parser (YAML → nx.DiGraph)
│   │   │   ├── middleware/
│   │   │   │   ├── auth.py           # JWT bearer token validation
│   │   │   │   ├── logging.py        # Structured JSON request logging
│   │   │   │   └── tracing.py        # OpenTelemetry span injection
│   │   │   ├── config.py             # Pydantic Settings (reads env vars + .apf/config.yaml)
│   │   │   └── deps.py               # FastAPI dependency injection (db session, event bus, etc.)
│   │   ├── tests/
│   │   │   ├── unit/
│   │   │   │   ├── test_engine.py
│   │   │   │   ├── test_dag.py
│   │   │   │   ├── test_retry.py
│   │   │   │   └── test_checkpoint.py
│   │   │   ├── integration/
│   │   │   │   ├── test_pipelines_api.py
│   │   │   │   ├── test_artifacts_api.py
│   │   │   │   └── test_websocket.py
│   │   │   └── conftest.py
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   │
│   ├── agent-runner/                 # Worker process: dequeues tasks, executes agent stages
│   │   ├── apf_agent_runner/
│   │   │   ├── __init__.py
│   │   │   ├── main.py               # Worker entrypoint (async loop consuming Redis Streams)
│   │   │   ├── runner.py             # AgentRunner: loads agent class, executes, emits result
│   │   │   ├── agents/               # Concrete agent implementations
│   │   │   │   ├── __init__.py
│   │   │   │   ├── prd.py            # PRDAgent
│   │   │   │   ├── architect.py      # ArchitectAgent
│   │   │   │   ├── market.py         # MarketAgent
│   │   │   │   ├── ux.py             # UXAgent
│   │   │   │   ├── engineering.py    # EngineeringAgent
│   │   │   │   ├── developer.py      # DeveloperAgent
│   │   │   │   ├── qa.py             # QAAgent
│   │   │   │   ├── regression.py     # RegressionAgent
│   │   │   │   ├── review.py         # ReviewAgent
│   │   │   │   ├── devops.py         # DevOpsAgent
│   │   │   │   └── readme.py         # ReadmeAgent
│   │   │   ├── sast/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── semgrep.py        # Semgrep runner wrapper
│   │   │   │   └── secret_scan.py    # Entropy + regex secret scanner
│   │   │   └── config.py
│   │   ├── tests/
│   │   │   ├── unit/
│   │   │   │   ├── test_prd_agent.py
│   │   │   │   ├── test_architect_agent.py
│   │   │   │   ├── test_developer_agent.py
│   │   │   │   ├── test_qa_agent.py
│   │   │   │   ├── test_review_agent.py
│   │   │   │   └── test_sast.py
│   │   │   ├── integration/
│   │   │   │   └── test_runner_pipeline.py
│   │   │   └── conftest.py           # LLM mock fixtures
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   │
│   ├── artifact-store/               # Artifact read/write API + storage backend abstraction
│   │   ├── apf_artifact_store/
│   │   │   ├── __init__.py
│   │   │   ├── main.py               # FastAPI app
│   │   │   ├── api/
│   │   │   │   ├── artifacts.py      # /api/v1/artifacts CRUD
│   │   │   │   └── health.py
│   │   │   ├── backends/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py           # StorageBackend Protocol
│   │   │   │   ├── local.py          # LocalFileSystemBackend
│   │   │   │   └── s3.py             # S3Backend (boto3)
│   │   │   └── config.py
│   │   ├── tests/
│   │   │   ├── unit/
│   │   │   │   ├── test_local_backend.py
│   │   │   │   └── test_s3_backend.py
│   │   │   └── integration/
│   │   │       └── test_artifacts_api.py
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   │
│   ├── github-integration/           # GitHub App webhook receiver + Git operations
│   │   ├── apf_github/
│   │   │   ├── __init__.py
│   │   │   ├── main.py               # FastAPI app
│   │   │   ├── api/
│   │   │   │   ├── webhooks.py       # POST /webhooks/github (HMAC-validated)
│   │   │   │   └── health.py
│   │   │   ├── client.py             # GitHub API client (PyGithub or httpx-based)
│   │   │   ├── git_ops.py            # Branch creation, commit, PR creation (GitPython)
│   │   │   └── config.py
│   │   ├── tests/
│   │   │   ├── unit/
│   │   │   │   ├── test_webhook_validation.py
│   │   │   │   ├── test_git_ops.py
│   │   │   │   └── test_pr_creation.py
│   │   │   └── integration/
│   │   │       └── test_github_api.py
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   │
│   ├── dashboard/                    # React web dashboard
│   │   ├── src/
│   │   │   ├── main.tsx
│   │   │   ├── App.tsx
│   │   │   ├── api/                  # API client (openapi-fetch generated + hand-written)
│   │   │   │   ├── client.ts
│   │   │   │   ├── pipelines.ts
│   │   │   │   ├── artifacts.ts
│   │   │   │   └── ws.ts             # WebSocket hook
│   │   │   ├── components/
│   │   │   │   ├── ui/               # shadcn/ui primitives (auto-generated)
│   │   │   │   ├── PipelineList/
│   │   │   │   │   ├── PipelineList.tsx
│   │   │   │   │   └── PipelineList.test.tsx
│   │   │   │   ├── PipelineDetail/
│   │   │   │   │   ├── PipelineDetail.tsx
│   │   │   │   │   ├── StageDAG.tsx  # reactflow DAG visualization
│   │   │   │   │   ├── LogViewer.tsx # xterm.js streaming log viewer
│   │   │   │   │   └── ArtifactViewer.tsx
│   │   │   │   ├── Settings/
│   │   │   │   │   ├── Settings.tsx
│   │   │   │   │   └── IntegrationStatus.tsx
│   │   │   │   └── Auth/
│   │   │   │       ├── LoginPage.tsx
│   │   │   │       └── AuthGuard.tsx
│   │   │   ├── hooks/
│   │   │   │   ├── usePipeline.ts
│   │   │   │   ├── useLiveLogs.ts
│   │   │   │   └── useAuth.ts
│   │   │   ├── stores/               # Zustand state stores
│   │   │   │   ├── pipelineStore.ts
│   │   │   │   └── authStore.ts
│   │   │   ├── pages/
│   │   │   │   ├── PipelinesPage.tsx
│   │   │   │   ├── PipelineDetailPage.tsx
│   │   │   │   ├── SettingsPage.tsx
│   │   │   │   └── LoginPage.tsx
│   │   │   └── lib/
│   │   │       ├── utils.ts
│   │   │       └── constants.ts
│   │   ├── public/
│   │   ├── tests/
│   │   │   ├── unit/
│   │   │   └── e2e/
│   │   │       ├── pipelines.spec.ts  # Playwright E2E
│   │   │       └── auth.spec.ts
│   │   ├── index.html
│   │   ├── vite.config.ts
│   │   ├── tailwind.config.ts
│   │   ├── tsconfig.json
│   │   ├── package.json
│   │   └── Dockerfile
│   │
│   ├── slack-connector/              # Slack App (bolt-python)
│   │   ├── apf_slack/
│   │   │   ├── __init__.py
│   │   │   ├── main.py               # Bolt app + FastAPI adapter
│   │   │   ├── handlers/
│   │   │   │   ├── commands.py       # /apf slash commands
│   │   │   │   ├── actions.py        # Interactive button callbacks (approve/reject)
│   │   │   │   └── notifications.py  # Outbound message builders
│   │   │   ├── pipeline_subscriber.py # Redis Streams consumer → Slack messages
│   │   │   └── config.py
│   │   ├── tests/
│   │   │   ├── test_commands.py
│   │   │   ├── test_actions.py
│   │   │   └── test_notifications.py
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   │
│   ├── jira-connector/               # Jira Cloud/Server sync
│   │   ├── apf_jira/
│   │   │   ├── __init__.py
│   │   │   ├── main.py               # FastAPI app + event subscriber
│   │   │   ├── client.py             # Jira REST API v3 client
│   │   │   ├── sync.py               # Epic/Story/Task creation logic
│   │   │   ├── webhook.py            # Inbound Jira webhook handler
│   │   │   └── config.py
│   │   ├── tests/
│   │   │   ├── test_sync.py
│   │   │   └── test_client.py
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   │
│   ├── confluence-connector/         # Confluence page publisher
│   │   ├── apf_confluence/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── client.py             # Confluence REST API v2 client
│   │   │   ├── publisher.py          # Markdown → Confluence Storage Format + page upsert
│   │   │   └── config.py
│   │   ├── tests/
│   │   │   ├── test_publisher.py
│   │   │   └── test_client.py
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   │
│   └── aws-connector/                # AWS deployment trigger
│       ├── apf_aws/
│       │   ├── __init__.py
│       │   ├── main.py
│       │   ├── deployer.py           # CodePipeline / ECS / Lambda deployment logic
│       │   ├── terraform.py          # terraform plan/apply subprocess wrapper
│       │   └── config.py
│       ├── tests/
│       │   ├── test_deployer.py
│       │   └── test_terraform.py
│       ├── Dockerfile
│       └── pyproject.toml
│
├── cli/                              # APF CLI (Python, Click-based)
│   ├── apf_cli/
│   │   ├── __init__.py
│   │   ├── main.py                   # Click group entrypoint
│   │   ├── commands/
│   │   │   ├── run.py                # apf run
│   │   │   ├── status.py             # apf status
│   │   │   ├── logs.py               # apf logs
│   │   │   ├── artifacts.py          # apf artifacts
│   │   │   ├── config.py             # apf config init|validate
│   │   │   ├── auth.py               # apf auth login|logout|whoami
│   │   │   └── integrations.py       # apf integrations list|enable|disable
│   │   ├── client.py                 # HTTP client wrapping orchestrator API
│   │   ├── output.py                 # Rich-based terminal renderer
│   │   └── config_schema.py          # .apf/config.yaml Pydantic schema
│   ├── tests/
│   │   ├── test_run_command.py
│   │   ├── test_status_command.py
│   │   └── test_config.py
│   ├── pyproject.toml                # includes `[project.scripts] apf = "apf_cli.main:cli"`
│   └── README.md
│
├── helm/
│   └── apf/                          # Helm chart for Kubernetes deployment
│       ├── Chart.yaml
│       ├── values.yaml
│       ├── values-production.yaml
│       └── templates/
│           ├── _helpers.tpl
│           ├── orchestrator-deployment.yaml
│           ├── agent-runner-deployment.yaml
│           ├── artifact-store-deployment.yaml
│           ├── dashboard-deployment.yaml
│           ├── redis-deployment.yaml
│           ├── postgres-statefulset.yaml
│           ├── ingress.yaml
│           └── secrets.yaml
│
├── deploy/
│   ├── docker-compose.yml            # Single-node self-hosted deployment
│   ├── docker-compose.dev.yml        # Developer override (hot-reload mounts)
│   ├── .env.example                  # Template for all required env vars
│   └── init-db.sh                    # Database initialization script
│
├── docs/
│   ├── prd.md
│   ├── market_analysis.md
│   ├── engineering_plan.md           # This document
│   ├── architecture.md               # System architecture (produced by architect agent)
│   ├── api-reference.md              # OpenAPI spec rendered as markdown
│   ├── deployment.md                 # Self-hosted deployment guide
│   ├── configuration.md              # Configuration reference
│   ├── contributing.md               # Contributor guide
│   └── adr/                          # Architecture Decision Records
│       ├── 0001-python-fastapi.md
│       ├── 0002-redis-streams.md
│       ├── 0003-sqlite-postgres-dual.md
│       └── 0004-agent-runner-separation.md
│
├── scripts/
│   ├── setup-dev.sh                  # One-command dev environment setup
│   ├── run-tests.sh                  # Run full test suite across all packages
│   ├── generate-openapi.sh           # Export OpenAPI JSON from running orchestrator
│   └── bump-version.sh               # Coordinated version bump across all pyproject.toml
│
├── .apf/
│   └── config.yaml.example           # Example APF config file for this repository itself
│
├── pyproject.toml                    # Root workspace config (uv workspace)
├── uv.lock                           # Pinned dependency lockfile
├── package.json                      # Root npm workspace config
├── pnpm-lock.yaml                    # Pinned frontend dependency lockfile
├── .pre-commit-config.yaml           # Pre-commit hooks (ruff, mypy, prettier)
├── .editorconfig
├── .gitignore
├── LICENSE                           # Apache 2.0
├── CHANGELOG.md
├── CONTRIBUTING.md
└── README.md
```

---

## 3. Services Build Order

### Phase 0: Foundations (Weeks 1–2)

**Goal:** Every developer can run tests, linting, and a local build from day one. No blocked work.

**Build:**
1. Repository scaffolding (directory structure, `pyproject.toml` workspace, `package.json` workspace)
2. `packages/db/` — ORM models + initial Alembic migration (all tables, even those needed by later phases)
3. `packages/event-bus/` — `EventBusClient` with in-memory stub for test environments
4. `packages/agent-core/` — `BaseAgent`, `LLMProvider` protocol, `PipelineContext`, all artifact Pydantic schemas, `AnthropicProvider` + `OpenAIProvider` stubs
5. CI skeleton: GitHub Actions `ci.yml` that runs `ruff`, `mypy`, `pytest` (empty test suites pass), and `vitest`
6. `deploy/.env.example` and `deploy/docker-compose.yml` skeleton (no working services yet)

**Why first:** All downstream services import from `packages/`. Defining schemas before implementation prevents interface drift. CI from day one prevents debt accumulation.

### Phase 1: Core Pipeline (Weeks 3–6)

**Goal:** A pipeline run triggered via internal API executes all 11 agent stages and persists results.

**Build order within phase:**
1. `services/artifact-store/` (local filesystem backend only)
2. `services/orchestrator/` core engine (`engine.py`, `dag.py`, `checkpoint.py`, `retry.py`)
3. `services/orchestrator/` REST API (`/api/v1/pipelines`, `/api/v1/stages`, `/api/v1/artifacts`, `/healthz`)
4. `services/agent-runner/` — all 11 agents (LLM-backed, with mock LLM in tests)
5. Redis Streams integration: orchestrator enqueues `stage.dispatch` events; agent-runner consumes
6. WebSocket endpoint on orchestrator for live pipeline status
7. Full `docker-compose.yml` with orchestrator + agent-runner + artifact-store + Redis + SQLite

**Why this order:** Artifact store must exist before agents can persist output. Orchestrator engine must exist before agent-runner has a queue to consume from. WebSocket is last within the phase because it depends on stable event schemas.

### Phase 2: GitHub Integration + CLI (Weeks 7–9)

**Goal:** `apf run "build a todo app"` creates a real GitHub PR with code.

**Build:**
1. `services/github-integration/` — webhook receiver, branch creation, commit, PR creation
2. Wire `DeveloperAgent` to call github-integration service for commits
3. Wire `ReviewAgent` to post PR review comments via GitHub API
4. `cli/` — all commands backed by orchestrator REST API
5. `apf config init` interactive wizard
6. `cli/` binary packaging + `pip install apf-cli` publishing setup (TestPyPI first)

### Phase 3: Web Dashboard (Weeks 10–12)

**Goal:** Browser dashboard shows live pipeline status, logs, and artifacts.

**Build:**
1. Dashboard React app scaffold (Vite + Tailwind + shadcn/ui)
2. Pipeline list page + API client (generated from OpenAPI spec)
3. Pipeline detail page with reactflow DAG
4. Streaming log viewer (WebSocket → xterm.js)
5. Artifact viewer (markdown render + syntax highlight)
6. Authentication (JWT login page, AuthGuard)
7. Settings page (connector status, config management)
8. Playwright E2E tests

### Phase 4: Connectors (Weeks 13–17)

**Build order:**
1. `services/slack-connector/` — notifications first, then slash commands, then interactive approvals
2. `services/jira-connector/` — Epic/Story creation, status transitions, PR linking
3. `services/confluence-connector/` — markdown-to-storage-format converter, page upsert
4. `services/aws-connector/` — CodePipeline trigger, ECS deploy, Lambda deploy, terraform wrapper
5. Connector enable/disable via orchestrator API and CLI
6. Human-in-the-loop gate: Slack approval blocks pipeline progression

**Why this order:** Slack is highest demand + highest distribution leverage per market analysis. Jira second (65% enterprise market share). Confluence third (complementary to Jira). AWS last (narrows TAM, most complex).

### Phase 5: Polish, Hardening, Docs (Weeks 18–20)

**Build:**
1. Prometheus `/metrics` endpoint and example AlertManager rules
2. OpenTelemetry tracing across orchestrator + agent-runner
3. S3 backend for artifact-store
4. PostgreSQL support validation + Helm chart completion
5. SAST integration in ReviewAgent (Semgrep)
6. Secret scanning in ReviewAgent (entropy + regex)
7. SBOM generation in release workflow
8. All documentation files (`docs/deployment.md`, `docs/configuration.md`, `docs/api-reference.md`)
9. `README.md` + `CONTRIBUTING.md`
10. `apf config validate` full validation
11. Load testing with Locust (5 concurrent pipelines target)

---

## 4. Service Specifications

### 4.1 `packages/agent-core`

**Files to create:**

| File | Purpose |
|---|---|
| `apf_agent_core/agent.py` | `BaseAgent(ABC)` with `execute(ctx: PipelineContext) -> Artifact` abstract method |
| `apf_agent_core/artifacts.py` | Pydantic models: `PRDArtifact`, `ArchitectureArtifact`, `MarketArtifact`, `UXArtifact`, `EngineeringArtifact`, `DeveloperArtifact`, `QAArtifact`, `RegressionArtifact`, `ReviewArtifact`, `DevOpsArtifact`, `ReadmeArtifact` |
| `apf_agent_core/context.py` | `PipelineContext(run_id, idea, artifacts: dict[str, Artifact], config, credentials)` |
| `apf_agent_core/llm/provider.py` | `LLMProvider` Protocol with `complete`, `stream`, `structured_output` |
| `apf_agent_core/llm/anthropic.py` | `AnthropicProvider` implementing `LLMProvider` |
| `apf_agent_core/llm/openai.py` | `OpenAIProvider` implementing `LLMProvider` |
| `apf_agent_core/llm/litellm.py` | `LiteLLMProvider` for all other models |
| `apf_agent_core/validators.py` | `validate_artifact(artifact, schema_class)` — raises `ArtifactValidationError` |

**Interfaces:**

```python
# agent.py
class BaseAgent(ABC):
    agent_name: ClassVar[str]
    output_artifact_class: ClassVar[type[BaseArtifact]]

    def __init__(self, llm: LLMProvider, config: AgentConfig): ...

    @abstractmethod
    async def execute(self, ctx: PipelineContext) -> BaseArtifact: ...

    async def _call_llm(self, system: str, user: str) -> str: ...
    async def _structured_output(self, system: str, user: str, schema: type[T]) -> T: ...

# context.py
@dataclass
class PipelineContext:
    run_id: str                          # UUID
    idea: str                            # Original natural language prompt
    artifacts: dict[str, BaseArtifact]  # Keyed by agent_name
    config: PipelineConfig
    credentials: CredentialStore         # Never serialised to disk
    metadata: dict[str, Any]             # Pipeline-level metadata
```

**LLMProvider interface:**

```python
class LLMProvider(Protocol):
    async def complete(
        self,
        messages: list[dict],
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> str: ...

    async def stream(
        self,
        messages: list[dict],
        model: str,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]: ...

    async def structured_output(
        self,
        messages: list[dict],
        schema: type[T],
        model: str,
        max_tokens: int = 4096,
    ) -> T: ...
```

**Test files:**

- `tests/test_agent.py` — `BaseAgent` subclass execution, context passing, error propagation
- `tests/test_artifacts.py` — Pydantic validation happy paths + invalid input rejection for each artifact type
- `tests/test_llm_provider.py` — `AnthropicProvider` and `OpenAIProvider` with `respx` HTTP mocks
- `tests/test_validators.py` — `validate_artifact` raises on missing required fields

**External dependencies (`pyproject.toml`):**

```toml
dependencies = [
    "pydantic>=2.7,<3",
    "anthropic>=0.27,<1",
    "openai>=1.30,<2",
    "litellm>=1.40,<2",
    "jinja2>=3.1,<4",
    "aiofiles>=23.0",
]
```

---

### 4.2 `packages/db`

**Files to create:**

| File | Purpose |
|---|---|
| `apf_db/models.py` | All SQLAlchemy 2.x ORM models (see Section 7) |
| `apf_db/session.py` | `async_session_factory`, `get_db()` dependency |
| `apf_db/migrations/env.py` | Alembic async migration environment |
| `apf_db/migrations/versions/0001_initial_schema.py` | Initial schema migration |

**Test files:**

- `tests/test_models.py` — CRUD operations against in-memory SQLite, relationship loading

**External dependencies:**

```toml
dependencies = [
    "sqlalchemy>=2.0,<3",
    "alembic>=1.13,<2",
    "aiosqlite>=0.20",       # SQLite async driver
    "asyncpg>=0.29",          # PostgreSQL async driver
]
```

---

### 4.3 `packages/event-bus`

**Files to create:**

| File | Purpose |
|---|---|
| `apf_event_bus/client.py` | `EventBusClient` with `publish(stream, event)`, `subscribe(stream, group, consumer)`, `ack(stream, group, msg_id)` |
| `apf_event_bus/schemas.py` | All event Pydantic schemas (see Section 6) |
| `apf_event_bus/streams.py` | Constants: `STREAM_STAGE_DISPATCH`, `STREAM_STAGE_RESULT`, `STREAM_PIPELINE_STATUS` |

**Interfaces:**

```python
class EventBusClient:
    async def publish(self, stream: str, event: BaseEvent) -> str: ...
    # Returns message ID

    async def subscribe(
        self,
        stream: str,
        group: str,
        consumer: str,
        count: int = 10,
        block_ms: int = 2000,
    ) -> AsyncIterator[tuple[str, BaseEvent]]: ...
    # Yields (message_id, event)

    async def ack(self, stream: str, group: str, msg_id: str) -> None: ...
```

**Test files:**

- `tests/test_event_bus.py` — publish/subscribe round-trip using a real Redis instance via `pytest-docker` or `fakeredis`

**External dependencies:**

```toml
dependencies = [
    "redis>=5.0,<6",
    "pydantic>=2.7,<3",
]
```

---

### 4.4 `services/orchestrator`

**Files to create:** (key files beyond the scaffolding listed in Section 2)

| File | Purpose |
|---|---|
| `core/engine.py` | `PipelineEngine.run(pipeline_id)` — loads DAG, dispatches stages via event bus, awaits results, checkpoints state |
| `core/dag.py` | `PipelineDAG.from_yaml(path)` — parses YAML pipeline definition into `nx.DiGraph`; `topological_stages()` |
| `core/scheduler.py` | `PipelineScheduler` — maintains asyncio semaphore for max concurrent runs (default: 5) |
| `core/checkpoint.py` | `save_checkpoint(run_id, stage, artifact)`, `load_checkpoint(run_id, stage)` |
| `core/retry.py` | `retry_with_backoff(coro, max_attempts, base_delay)` |
| `api/pipelines.py` | Pipeline CRUD + trigger endpoints |
| `api/websocket.py` | `/ws/pipelines/{run_id}` — broadcasts pipeline events to connected clients |

**Key interface: `PipelineEngine`**

```python
class PipelineEngine:
    async def run(
        self,
        pipeline_id: str,
        idea: str,
        config: PipelineRunConfig,
        resume_from: str | None = None,
    ) -> PipelineRun: ...

    async def cancel(self, pipeline_id: str) -> None: ...

    async def get_status(self, pipeline_id: str) -> PipelineStatus: ...
```

**Test files (unit):**

- `tests/unit/test_engine.py` — full pipeline execution with mock event bus + mock agents; resume from checkpoint; cancel mid-run
- `tests/unit/test_dag.py` — YAML parsing, topological ordering, invalid DAG detection
- `tests/unit/test_retry.py` — exponential backoff timing, max attempts respected, exception propagation
- `tests/unit/test_checkpoint.py` — save/load round-trip, missing checkpoint returns None

**Test files (integration):**

- `tests/integration/test_pipelines_api.py` — POST `/api/v1/pipelines`, GET `/api/v1/pipelines/{id}`, cancel endpoint; uses in-process ASGI client
- `tests/integration/test_websocket.py` — WS connection, receives stage events during mock run

**External dependencies:**

```toml
dependencies = [
    "fastapi>=0.111,<1",
    "uvicorn[standard]>=0.30",
    "pydantic-settings>=2.2",
    "networkx>=3.3",
    "apf-db",                  # workspace package
    "apf-event-bus",           # workspace package
    "apf-agent-core",          # workspace package
    "python-jose[cryptography]>=3.3",   # JWT
    "passlib[bcrypt]>=1.7",
    "opentelemetry-sdk>=1.24",
    "opentelemetry-instrumentation-fastapi>=0.45",
    "prometheus-fastapi-instrumentator>=7.0",
]
```

---

### 4.5 `services/agent-runner`

**Each agent follows this pattern:**

```python
class PRDAgent(BaseAgent):
    agent_name = "prd"
    output_artifact_class = PRDArtifact

    async def execute(self, ctx: PipelineContext) -> PRDArtifact:
        system = self._render_prompt("prd.j2", ctx=ctx)
        user = f"Transform this idea into a complete PRD:\n\n{ctx.idea}"
        result = await self._structured_output(
            messages=[{"role": "user", "content": user}],
            schema=PRDArtifact,
        )
        return result
```

**Runner loop:**

```python
# runner.py
async def run_worker():
    async for msg_id, event in bus.subscribe(STREAM_STAGE_DISPATCH, "agent-runner", worker_id):
        agent_class = AGENT_REGISTRY[event.stage_name]
        agent = agent_class(llm=build_llm_provider(event.config), config=event.agent_config)
        try:
            artifact = await agent.execute(event.context)
            await bus.publish(STREAM_STAGE_RESULT, StageResultEvent(
                pipeline_id=event.pipeline_id,
                stage_name=event.stage_name,
                status="completed",
                artifact=artifact,
            ))
        except Exception as e:
            await bus.publish(STREAM_STAGE_RESULT, StageResultEvent(
                pipeline_id=event.pipeline_id,
                stage_name=event.stage_name,
                status="failed",
                error=str(e),
            ))
        finally:
            await bus.ack(STREAM_STAGE_DISPATCH, "agent-runner", msg_id)
```

**SAST interface:**

```python
# sast/semgrep.py
async def run_semgrep(code_dir: Path, config: str = "auto") -> SemgrepReport: ...
# Returns: findings: list[Finding(rule_id, severity, file, line, message)]

# sast/secret_scan.py
def scan_for_secrets(content: str) -> list[SecretFinding]: ...
# Applies: high-entropy string detection, regex patterns (API keys, tokens, passwords)
```

**Test files:**

Each agent has a dedicated test file with:
1. A mock `LLMProvider` that returns a fixture response
2. Assertion that the output validates against the artifact schema
3. Assertion that quality gates (required sections, minimum content) are checked

---

### 4.6 `services/artifact-store`

**Storage backend interface:**

```python
class StorageBackend(Protocol):
    async def write(self, key: str, data: bytes, content_type: str) -> str: ...
    # Returns: storage URI

    async def read(self, key: str) -> tuple[bytes, str]: ...
    # Returns: (data, content_type)

    async def delete(self, key: str) -> None: ...

    async def list(self, prefix: str) -> list[str]: ...
    # Returns: list of keys matching prefix
```

Key naming convention: `{run_id}/{stage_name}/{artifact_name}`

**Test files:**

- `tests/unit/test_local_backend.py` — write/read/delete/list against a `tmp_path` fixture
- `tests/unit/test_s3_backend.py` — write/read against moto-mocked S3
- `tests/integration/test_artifacts_api.py` — full HTTP round-trip via ASGI test client

---

### 4.7 `services/github-integration`

**Key interfaces:**

```python
# client.py
class GitHubClient:
    async def create_branch(self, repo: str, branch: str, base: str) -> None: ...
    async def commit_files(
        self,
        repo: str,
        branch: str,
        files: dict[str, str],  # path -> content
        message: str,
    ) -> str: ...  # Returns commit SHA

    async def create_pull_request(
        self,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
        labels: list[str],
    ) -> PullRequest: ...

    async def create_review(
        self,
        repo: str,
        pr_number: int,
        body: str,
        comments: list[ReviewComment],
        event: Literal["APPROVE", "REQUEST_CHANGES", "COMMENT"],
    ) -> None: ...
```

**Webhook validation:**

```python
def validate_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), payload, "sha256").hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

### 4.8 `cli/`

**CLI command signatures:**

```
apf run "<idea>" [--stage STAGE] [--from STAGE] [--config PATH] [--json] [--quiet]
apf status [RUN_ID] [--watch] [--json]
apf logs RUN_ID [--stage STAGE] [--level LEVEL] [--follow]
apf artifacts RUN_ID [--stage STAGE] [--output DIR]
apf config init [--global]
apf config validate [--config PATH]
apf auth login [--token TOKEN]
apf auth logout
apf auth whoami
apf integrations list
apf integrations enable <NAME> [--config KEY=VALUE ...]
apf integrations disable <NAME>
```

**Output format (default: Rich terminal UI):**

```
[APF] Starting pipeline run run-abc123
[PRD      ] ⣾ Running...
[PRD      ] ✓ Completed in 12.3s
[ARCHITECT] ⣾ Running...
```

**JSON output format (--json flag):**

```json
{
  "event": "stage_completed",
  "run_id": "run-abc123",
  "stage": "prd",
  "duration_ms": 12340,
  "status": "completed"
}
```

---

### 4.9 `services/slack-connector`

**Bolt slash command handlers:**

```python
@app.command("/apf")
async def handle_apf_command(ack, command, client, logger):
    await ack()
    subcommand, *args = command["text"].split(maxsplit=1)
    match subcommand:
        case "run":    await handle_run(args[0], command, client)
        case "status": await handle_status(args[0] if args else None, command, client)
        case "approve": await handle_approve(args[0], command, client)
        case "cancel": await handle_cancel(args[0], command, client)
```

**Notification message block templates (defined as Jinja2 templates in `handlers/notifications.py`):**
- `pipeline_started.j2` — fields: run_id, idea_summary, initiator, estimated_duration
- `stage_completed.j2` — fields: stage_name, duration, status (posted as thread reply)
- `pipeline_completed.j2` — fields: run_id, pr_url, dashboard_url, artifact_count
- `pipeline_failed.j2` — fields: stage_name, error_summary, logs_url
- `approval_request.j2` — includes Approve / Reject interactive buttons

---

### 4.10 `services/jira-connector`

**Jira API calls:**

```python
# sync.py
async def create_epic(pipeline: PipelineRun) -> str: ...        # Returns Jira issue key
async def create_stories(epic_key: str, plan: EngineeringArtifact) -> list[str]: ...
async def create_tasks(story_key: str, tasks: list[Task]) -> list[str]: ...
async def transition_issue(issue_key: str, transition_name: str) -> None: ...
async def add_remote_link(issue_key: str, url: str, title: str) -> None: ...
async def attach_file(issue_key: str, filename: str, content: bytes) -> None: ...
```

Story point mapping: `S=1`, `M=3`, `L=8`, `XL=13`

---

### 4.11 `services/confluence-connector`

**Key conversion:**

```python
# publisher.py
def markdown_to_storage_format(markdown: str) -> str: ...
# Uses: mistune 3.x for parsing, custom renderer for Confluence XHTML output
# Preserves: headings, code blocks (with language), tables, mermaid (as image macro)

async def upsert_page(
    space_key: str,
    parent_id: str,
    title: str,
    content: str,
) -> ConfluencePage: ...
# Creates if not exists; updates (increments version) if exists
```

---

### 4.12 `services/aws-connector`

**Deployer interface:**

```python
class AWSDeployer:
    async def deploy_codepipeline(self, pipeline_name: str) -> Execution: ...
    async def deploy_ecs(
        self,
        cluster: str,
        service: str,
        image_tag: str,
    ) -> Deployment: ...
    async def deploy_lambda(
        self,
        function_name: str,
        zip_path: Path,
    ) -> FunctionVersion: ...
    async def poll_deployment(self, deployment: Deployment) -> DeploymentStatus: ...
    async def rollback(self, deployment: Deployment) -> None: ...
```

---

## 5. API Contracts

All endpoints are prefixed with `/api/v1`. All requests require `Authorization: Bearer <token>` header unless noted. All responses are `Content-Type: application/json`.

### 5.1 Authentication

#### `POST /api/v1/auth/token`

**Purpose:** Exchange username + password for a JWT access token.

**Request body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response `200`:**
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "uuid",
    "username": "string",
    "role": "viewer | operator | admin"
  }
}
```

**Errors:** `401 Unauthorized` (invalid credentials), `422 Unprocessable Entity` (validation)

---

#### `POST /api/v1/auth/refresh`

**Request body:** `{ "refresh_token": "string" }`
**Response `200`:** Same as `POST /auth/token`
**Errors:** `401` (expired/invalid refresh token)

---

### 5.2 Pipelines

#### `POST /api/v1/pipelines`

**Purpose:** Trigger a new pipeline run.

**Required role:** `operator`

**Request body:**
```json
{
  "idea": "string (1–10000 chars)",
  "pipeline_template": "default | string (optional, default: 'default')",
  "stages_disabled": ["string"] ,
  "resume_from_run_id": "uuid (optional)",
  "resume_from_stage": "string (optional)",
  "config_overrides": {
    "llm_provider": "anthropic | openai | litellm (optional)",
    "llm_model": "string (optional)",
    "max_tokens": "integer (optional)"
  },
  "tags": ["string"]
}
```

**Response `201`:**
```json
{
  "id": "uuid",
  "status": "queued",
  "idea": "string",
  "created_at": "ISO8601",
  "estimated_duration_seconds": 900,
  "stages": [
    {
      "name": "prd",
      "status": "pending",
      "order": 1
    }
  ],
  "links": {
    "self": "/api/v1/pipelines/{id}",
    "logs": "/api/v1/pipelines/{id}/logs",
    "websocket": "/ws/pipelines/{id}"
  }
}
```

**Errors:** `400 Bad Request` (invalid idea/config), `401`, `403 Forbidden` (insufficient role), `429 Too Many Requests` (concurrent limit reached)

---

#### `GET /api/v1/pipelines`

**Purpose:** List pipeline runs.

**Required role:** `viewer`

**Query parameters:**
- `status`: `queued | running | completed | failed | cancelled` (optional, multi-value)
- `from`: ISO8601 datetime (optional)
- `to`: ISO8601 datetime (optional)
- `tag`: string (optional, multi-value)
- `page`: integer (default: 1)
- `page_size`: integer (default: 20, max: 100)
- `sort`: `created_at | updated_at | duration` (default: `created_at`)
- `order`: `asc | desc` (default: `desc`)

**Response `200`:**
```json
{
  "items": [
    {
      "id": "uuid",
      "status": "completed",
      "idea": "string",
      "created_at": "ISO8601",
      "updated_at": "ISO8601",
      "duration_seconds": 487,
      "pr_url": "string | null",
      "tags": ["string"],
      "stage_summary": {
        "total": 11,
        "completed": 11,
        "failed": 0
      }
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 142,
    "total_pages": 8
  }
}
```

---

#### `GET /api/v1/pipelines/{pipeline_id}`

**Purpose:** Get full pipeline run detail.

**Response `200`:**
```json
{
  "id": "uuid",
  "status": "completed | running | failed | cancelled | queued",
  "idea": "string",
  "created_at": "ISO8601",
  "updated_at": "ISO8601",
  "completed_at": "ISO8601 | null",
  "duration_seconds": 487,
  "pr_url": "string | null",
  "pr_number": "integer | null",
  "branch_name": "string | null",
  "tags": ["string"],
  "config": {
    "pipeline_template": "string",
    "llm_provider": "string",
    "llm_model": "string"
  },
  "stages": [
    {
      "name": "prd",
      "status": "completed",
      "order": 1,
      "started_at": "ISO8601 | null",
      "completed_at": "ISO8601 | null",
      "duration_seconds": 18,
      "attempts": 1,
      "agent_model": "claude-3-5-sonnet-20241022",
      "input_token_count": 1240,
      "output_token_count": 3820,
      "artifact_id": "uuid | null"
    }
  ],
  "error": "string | null"
}
```

**Errors:** `404 Not Found`

---

#### `DELETE /api/v1/pipelines/{pipeline_id}`

**Purpose:** Cancel a running pipeline.

**Required role:** `operator`

**Response `200`:** `{ "status": "cancelling" }`
**Errors:** `404`, `409 Conflict` (pipeline already completed/failed)

---

#### `GET /api/v1/pipelines/{pipeline_id}/logs`

**Purpose:** Retrieve agent logs for a pipeline run.

**Query parameters:**
- `stage`: string (optional, filter to single stage)
- `level`: `debug | info | warn | error` (optional)
- `limit`: integer (default: 500)
- `cursor`: string (optional, for pagination)

**Response `200`:**
```json
{
  "items": [
    {
      "timestamp": "ISO8601",
      "stage": "prd",
      "level": "info",
      "message": "string",
      "metadata": {}
    }
  ],
  "next_cursor": "string | null"
}
```

---

### 5.3 Stages

#### `GET /api/v1/stages/{stage_run_id}`

**Response `200`:**
```json
{
  "id": "uuid",
  "pipeline_id": "uuid",
  "name": "prd",
  "status": "completed",
  "started_at": "ISO8601",
  "completed_at": "ISO8601",
  "duration_seconds": 18,
  "attempts": 1,
  "agent_model": "string",
  "input_token_count": 1240,
  "output_token_count": 3820,
  "artifact_id": "uuid"
}
```

---

#### `POST /api/v1/stages/{stage_run_id}/retry`

**Purpose:** Manually retry a failed stage.

**Required role:** `operator`

**Request body:** `{}` (empty, uses original stage config)

**Response `202`:** `{ "status": "queued" }`
**Errors:** `409` (stage not in failed state)

---

### 5.4 Artifacts

#### `GET /api/v1/artifacts/{artifact_id}`

**Response `200`:**
```json
{
  "id": "uuid",
  "pipeline_id": "uuid",
  "stage_name": "prd",
  "artifact_name": "prd.md",
  "content_type": "text/markdown",
  "size_bytes": 14820,
  "storage_uri": "string (internal)",
  "created_at": "ISO8601",
  "sha256": "string"
}
```

---

#### `GET /api/v1/artifacts/{artifact_id}/content`

**Purpose:** Download artifact content.

**Response:** Raw file content with appropriate `Content-Type` header.

---

#### `GET /api/v1/pipelines/{pipeline_id}/artifacts`

**Purpose:** List all artifacts for a pipeline run.

**Response `200`:**
```json
{
  "items": [
    {
      "id": "uuid",
      "stage_name": "prd",
      "artifact_name": "prd.md",
      "content_type": "text/markdown",
      "size_bytes": 14820
    }
  ]
}
```

---

#### `GET /api/v1/pipelines/{pipeline_id}/artifacts/archive`

**Purpose:** Download all artifacts as a ZIP archive.

**Response:** `application/zip` binary stream.

---

### 5.5 Connectors

#### `GET /api/v1/connectors`

**Response `200`:**
```json
{
  "items": [
    {
      "name": "slack",
      "enabled": true,
      "status": "connected | error | unconfigured",
      "last_checked_at": "ISO8601",
      "error": "string | null"
    }
  ]
}
```

---

#### `PUT /api/v1/connectors/{name}`

**Purpose:** Enable/disable and configure a connector.

**Required role:** `admin`

**Request body:**
```json
{
  "enabled": true,
  "config": {
    "slack_bot_token": "env:SLACK_BOT_TOKEN",
    "slack_channel_id": "C0123ABC"
  }
}
```

**Response `200`:** Updated connector object (same as list item shape)

**Errors:** `400` (unknown connector name), `422` (invalid config schema for the connector)

---

#### `POST /api/v1/connectors/{name}/test`

**Purpose:** Test connectivity of a configured connector.

**Required role:** `admin`

**Response `200`:** `{ "success": true, "message": "string" }`
**Response `200` (failed test):** `{ "success": false, "message": "error detail" }`

---

### 5.6 Health

#### `GET /healthz`

**Auth:** None required.

**Response `200`:** `{ "status": "ok" }`
**Response `503`:** `{ "status": "degraded", "details": { "db": "ok", "redis": "error" } }`

---

#### `GET /readyz`

**Auth:** None required.

**Response `200`:** `{ "status": "ready" }`
**Response `503`:** `{ "status": "not_ready", "reason": "string" }`

---

#### `GET /metrics`

**Auth:** None required (restrict by network policy in production).

**Response:** Prometheus text format (`text/plain; version=0.0.4`)

---

### 5.7 WebSocket: Live Pipeline Events

#### `WS /ws/pipelines/{pipeline_id}`

**Auth:** Bearer token via `Authorization` header on upgrade request (or `?token=` query param for browser clients).

**Server-sent message types:**

```json
{ "type": "connected", "pipeline_id": "uuid", "current_status": "running" }

{ "type": "stage_started", "stage": "prd", "started_at": "ISO8601" }

{ "type": "stage_log", "stage": "prd", "level": "info", "message": "string", "timestamp": "ISO8601" }

{ "type": "stage_completed", "stage": "prd", "duration_seconds": 18, "artifact_id": "uuid" }

{ "type": "stage_failed", "stage": "prd", "error": "string", "attempts": 1 }

{ "type": "pipeline_completed", "pr_url": "string", "duration_seconds": 487 }

{ "type": "pipeline_failed", "stage": "prd", "error": "string" }

{ "type": "approval_required", "stage": "architect", "timeout_seconds": 3600 }
```

---

### 5.8 GitHub Webhook Receiver

#### `POST /webhooks/github`

**Auth:** HMAC-SHA256 signature via `X-Hub-Signature-256` header (GitHub App secret).

**Handled event types:**
- `issues` (`labeled` action, label = `apf-build`) → triggers pipeline run from issue body
- `pull_request` (`closed`, `merged=true`) → triggers AWS connector deployment
- `ping` → returns `200 OK`

**Response `200`:** `{ "received": true }`
**Response `401`:** Invalid signature.

---

## 6. Event Schemas

All events are serialized as JSON and published to Redis Streams. The `event_type` field is the stream message type. All events include a common header.

**Common header fields (all events):**
```json
{
  "event_id": "uuid",
  "event_type": "string",
  "timestamp": "ISO8601",
  "pipeline_id": "uuid",
  "version": "1"
}
```

---

### 6.1 `stage.dispatch`

**Stream:** `apf:stage:dispatch`

**Producer:** Orchestrator (`engine.py`)

**Consumer:** Agent Runner

**Payload:**
```json
{
  "event_id": "uuid",
  "event_type": "stage.dispatch",
  "timestamp": "ISO8601",
  "pipeline_id": "uuid",
  "stage_run_id": "uuid",
  "stage_name": "prd | architect | market | ux | engineering | developer | qa | regression | review | devops | readme",
  "attempt_number": 1,
  "context": {
    "run_id": "uuid",
    "idea": "string",
    "artifacts": {
      "prd": { ... }
    },
    "config": {
      "llm_provider": "anthropic",
      "llm_model": "claude-3-5-sonnet-20241022",
      "max_tokens": 8192,
      "temperature": 0.3
    }
  }
}
```

---

### 6.2 `stage.result`

**Stream:** `apf:stage:result`

**Producer:** Agent Runner

**Consumer:** Orchestrator

**Payload:**
```json
{
  "event_id": "uuid",
  "event_type": "stage.result",
  "timestamp": "ISO8601",
  "pipeline_id": "uuid",
  "stage_run_id": "uuid",
  "stage_name": "string",
  "status": "completed | failed",
  "attempt_number": 1,
  "duration_ms": 18340,
  "artifact": { ... },
  "artifact_id": "uuid | null",
  "error": "string | null",
  "token_usage": {
    "input_tokens": 1240,
    "output_tokens": 3820
  }
}
```

---

### 6.3 `stage.log`

**Stream:** `apf:stage:log`

**Producer:** Agent Runner (during stage execution)

**Consumer:** Orchestrator (persists to DB), WebSocket broadcaster, Slack connector (for failure notifications)

**Payload:**
```json
{
  "event_id": "uuid",
  "event_type": "stage.log",
  "timestamp": "ISO8601",
  "pipeline_id": "uuid",
  "stage_run_id": "uuid",
  "stage_name": "string",
  "level": "debug | info | warn | error",
  "message": "string",
  "metadata": {}
}
```

---

### 6.4 `pipeline.status_changed`

**Stream:** `apf:pipeline:status`

**Producer:** Orchestrator

**Consumer:** Slack connector, Jira connector, Confluence connector, AWS connector, WebSocket broadcaster

**Payload:**
```json
{
  "event_id": "uuid",
  "event_type": "pipeline.status_changed",
  "timestamp": "ISO8601",
  "pipeline_id": "uuid",
  "previous_status": "queued | running | completed | failed | cancelled",
  "new_status": "queued | running | completed | failed | cancelled",
  "idea": "string",
  "initiated_by": "string",
  "pr_url": "string | null",
  "branch_name": "string | null",
  "duration_seconds": 487,
  "failed_stage": "string | null",
  "error": "string | null"
}
```

---

### 6.5 `pipeline.approval_requested`

**Stream:** `apf:pipeline:approval`

**Producer:** Orchestrator (when a human-in-the-loop gate is reached)

**Consumer:** Slack connector

**Payload:**
```json
{
  "event_id": "uuid",
  "event_type": "pipeline.approval_requested",
  "timestamp": "ISO8601",
  "pipeline_id": "uuid",
  "gate_stage": "string",
  "requestor_channel": "string",
  "timeout_seconds": 3600,
  "context_summary": "string",
  "artifact_url": "string | null"
}
```

---

### 6.6 `pipeline.approval_responded`

**Stream:** `apf:pipeline:approval`

**Producer:** Slack connector (on user button click)

**Consumer:** Orchestrator

**Payload:**
```json
{
  "event_id": "uuid",
  "event_type": "pipeline.approval_responded",
  "timestamp": "ISO8601",
  "pipeline_id": "uuid",
  "gate_stage": "string",
  "decision": "approved | rejected",
  "decided_by": "string (Slack user ID)",
  "comment": "string | null"
}
```

---

### 6.7 `connector.action`

**Stream:** `apf:connector:action`

**Producer:** Orchestrator (on stage completion or pipeline completion)

**Consumer:** Individual connector services (each filters by `connector_name`)

**Payload:**
```json
{
  "event_id": "uuid",
  "event_type": "connector.action",
  "timestamp": "ISO8601",
  "pipeline_id": "uuid",
  "connector_name": "slack | jira | confluence | aws",
  "action": "string",
  "payload": {}
}
```

---

## 7. Database Schemas

All tables use UUID primary keys. Timestamps are stored as UTC with timezone. `JSONB` columns are used in PostgreSQL; `JSON` TEXT in SQLite.

### 7.1 `pipelines`

```sql
CREATE TABLE pipelines (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    idea            TEXT            NOT NULL,
    status          VARCHAR(20)     NOT NULL DEFAULT 'queued',
                    -- CHECK status IN ('queued','running','completed','failed','cancelled','paused')
    pipeline_template VARCHAR(100)  NOT NULL DEFAULT 'default',
    config          JSONB           NOT NULL DEFAULT '{}',
    tags            JSONB           NOT NULL DEFAULT '[]',
    initiated_by    VARCHAR(255),
    pr_url          TEXT,
    pr_number       INTEGER,
    branch_name     TEXT,
    failed_stage    VARCHAR(100),
    error_message   TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    duration_seconds INTEGER
);

CREATE INDEX idx_pipelines_status ON pipelines(status);
CREATE INDEX idx_pipelines_created_at ON pipelines(created_at DESC);
```

---

### 7.2 `stages`

```sql
CREATE TABLE stages (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id     UUID            NOT NULL REFERENCES pipelines(id) ON DELETE CASCADE,
    name            VARCHAR(100)    NOT NULL,
    status          VARCHAR(20)     NOT NULL DEFAULT 'pending',
                    -- CHECK status IN ('pending','queued','running','completed','failed','skipped')
    stage_order     INTEGER         NOT NULL,
    attempt_number  INTEGER         NOT NULL DEFAULT 1,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    duration_seconds INTEGER,
    agent_model     VARCHAR(255),
    input_token_count  INTEGER,
    output_token_count INTEGER,
    artifact_id     UUID            REFERENCES artifacts(id),
    error_message   TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_stages_pipeline_id ON stages(pipeline_id);
CREATE INDEX idx_stages_status ON stages(status);
CREATE UNIQUE INDEX idx_stages_pipeline_name_attempt
    ON stages(pipeline_id, name, attempt_number);
```

---

### 7.3 `artifacts`

```sql
CREATE TABLE artifacts (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id     UUID            NOT NULL REFERENCES pipelines(id) ON DELETE CASCADE,
    stage_name      VARCHAR(100)    NOT NULL,
    artifact_name   VARCHAR(255)    NOT NULL,
    content_type    VARCHAR(255)    NOT NULL,
    storage_uri     TEXT            NOT NULL,
    size_bytes      BIGINT          NOT NULL DEFAULT 0,
    sha256          CHAR(64)        NOT NULL,
    metadata        JSONB           NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_artifacts_pipeline_id ON artifacts(pipeline_id);
CREATE INDEX idx_artifacts_stage_name ON artifacts(pipeline_id, stage_name);
```

---

### 7.4 `agent_runs`

```sql
CREATE TABLE agent_runs (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    stage_id        UUID            NOT NULL REFERENCES stages(id) ON DELETE CASCADE,
    pipeline_id     UUID            NOT NULL REFERENCES pipelines(id) ON DELETE CASCADE,
    stage_name      VARCHAR(100)    NOT NULL,
    worker_id       VARCHAR(255),
    llm_provider    VARCHAR(100),
    llm_model       VARCHAR(255),
    prompt_hash     CHAR(64),       -- SHA256 of rendered system+user prompt
    input_token_count  INTEGER,
    output_token_count INTEGER,
    latency_ms      INTEGER,
    status          VARCHAR(20)     NOT NULL,
    error_message   TEXT,
    raw_llm_response TEXT,          -- Stored for debugging; truncated at 64KB
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_agent_runs_stage_id ON agent_runs(stage_id);
CREATE INDEX idx_agent_runs_pipeline_id ON agent_runs(pipeline_id);
```

---

### 7.5 `connector_configs`

```sql
CREATE TABLE connector_configs (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100)    NOT NULL UNIQUE,
                    -- 'slack' | 'jira' | 'confluence' | 'aws' | 'github'
    enabled         BOOLEAN         NOT NULL DEFAULT false,
    config          JSONB           NOT NULL DEFAULT '{}',
                    -- Encrypted at application layer before storage
                    -- Values prefixed 'env:' are resolved at runtime from environment
    status          VARCHAR(20)     NOT NULL DEFAULT 'unconfigured',
                    -- 'connected' | 'error' | 'unconfigured'
    last_checked_at TIMESTAMPTZ,
    last_error      TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
```

---

### 7.6 `audit_log`

```sql
CREATE TABLE audit_log (
    id              BIGSERIAL       PRIMARY KEY,  -- Sequential for ordering; NOT UUID
    timestamp       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    actor           VARCHAR(255),   -- Username or 'system' or 'agent:<stage_name>'
    action          VARCHAR(100)    NOT NULL,
                    -- 'pipeline.created' | 'pipeline.cancelled' | 'stage.started' |
                    -- 'stage.completed' | 'stage.failed' | 'artifact.created' |
                    -- 'connector.enabled' | 'connector.disabled' | 'approval.granted' |
                    -- 'approval.rejected' | 'user.login' | 'config.updated'
    resource_type   VARCHAR(100),   -- 'pipeline' | 'stage' | 'artifact' | 'connector'
    resource_id     UUID,
    pipeline_id     UUID,           -- Denormalized for fast pipeline-scoped queries
    detail          JSONB           NOT NULL DEFAULT '{}',
    ip_address      INET,
    user_agent      TEXT
);

CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_log_pipeline_id ON audit_log(pipeline_id) WHERE pipeline_id IS NOT NULL;
CREATE INDEX idx_audit_log_actor ON audit_log(actor);
-- Note: audit_log is append-only; no UPDATE or DELETE is permitted at the application layer.
```

---

### 7.7 `users`

```sql
CREATE TABLE users (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(255)    NOT NULL UNIQUE,
    email           VARCHAR(255)    UNIQUE,
    password_hash   TEXT,           -- bcrypt; NULL if SSO-only
    role            VARCHAR(20)     NOT NULL DEFAULT 'viewer',
                    -- CHECK role IN ('viewer','operator','admin')
    is_active       BOOLEAN         NOT NULL DEFAULT true,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
```

---

### 7.8 `pipeline_templates`

```sql
CREATE TABLE pipeline_templates (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100)    NOT NULL UNIQUE,
    description     TEXT,
    definition      JSONB           NOT NULL,
                    -- DAG definition: { stages: [{name, dependencies, config}] }
    is_default      BOOLEAN         NOT NULL DEFAULT false,
    version         INTEGER         NOT NULL DEFAULT 1,
    created_by      UUID            REFERENCES users(id),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
```

---

## 8. Testing Strategy

### 8.1 Unit Test Targets and Coverage Requirements

| Service/Package | Coverage Target | Key Test Areas |
|---|---|---|
| `packages/agent-core` | 90% | `BaseAgent` execution contract, all artifact schemas, `LLMProvider` mock responses, `PipelineContext` serialization |
| `packages/db` | 85% | All ORM CRUD operations, relationship loading, migration idempotency |
| `packages/event-bus` | 90% | Publish/subscribe/ack round-trips, consumer group creation, error on invalid schema |
| `services/orchestrator` core | 90% | `PipelineEngine` DAG execution, stage dispatch, checkpoint save/restore, retry logic, concurrent run semaphore |
| `services/orchestrator` API | 85% | All endpoints: happy paths + error codes; JWT auth enforcement; WebSocket message delivery |
| `services/agent-runner` agents | 85% | Each agent: schema-valid output from mocked LLM; quality gate enforcement; SAST integration |
| `services/artifact-store` | 90% | Local backend write/read/delete/list; S3 backend write/read (moto mocks); key naming |
| `services/github-integration` | 85% | Webhook HMAC validation; branch creation; commit; PR creation; review comment posting |
| `cli/` | 80% | All command argument parsing; API client calls; output formatting; config file read/write |
| `services/slack-connector` | 80% | Slash command parsing; notification message assembly; approval request/response flow |
| `services/jira-connector` | 80% | Epic/Story/Task creation; story point mapping; status transitions; PR link attachment |
| `services/confluence-connector` | 80% | Markdown → storage format conversion; page upsert (create vs update); version increment |
| `services/aws-connector` | 75% | CodePipeline trigger; ECS deploy; Lambda deploy; deployment poll; rollback |

### 8.2 Integration Test Plan

Integration tests run in CI against real service instances (spun up via `docker-compose` in a dedicated test environment). They are separated from unit tests and run in a `[integration]` marker group.

**Test matrix:**

| Test Suite | Services Involved | Data Strategy |
|---|---|---|
| `test_full_pipeline_run` | orchestrator + agent-runner + artifact-store + SQLite/Redis | Mock LLM provider; fixture idea prompt; assert all 11 stages complete and artifacts persist |
| `test_pipeline_resume` | orchestrator + agent-runner + artifact-store | Run to stage 3, kill runner, restart, assert resume from stage 4 |
| `test_pipeline_concurrent` | orchestrator + 3× agent-runner | Start 5 pipelines simultaneously; assert all complete; assert semaphore cap enforced |
| `test_github_webhook_trigger` | orchestrator + github-integration | Simulate `issues.labeled` webhook; assert pipeline created |
| `test_github_pr_creation` | agent-runner (developer) + github-integration | Run developer agent against fixture code; assert PR created on test repo (using GitHub test organization) |
| `test_slack_notification_flow` | orchestrator + slack-connector | Start pipeline; assert Slack messages sent (mock Slack API via respx) |
| `test_jira_epic_creation` | orchestrator + jira-connector | Complete engineering stage; assert Epic + Stories created (mock Jira API) |

### 8.3 Contract Testing

**Approach:** OpenAPI-based contract testing using `schemathesis` for server-side and `pact-python` for consumer-driven contracts.

**Server-side (schemathesis):**
- `schemathesis run /api/v1/openapi.json --checks all --stateful=links`
- Runs against a live test instance in CI; generates fuzz inputs for all endpoints
- Required to pass (zero 5xx responses on valid inputs) before merge to main

**Consumer-driven (pact-python):**
- The CLI (`apf_cli`) is the primary consumer of the orchestrator API
- Pacts are defined in `cli/tests/pacts/` and describe the exact request/response shapes the CLI depends on
- The orchestrator verifies all CLI pacts on every CI run
- The dashboard TypeScript client also generates pacts from its API calls, verified by the orchestrator

**Contract locations:**
- `cli/tests/pacts/apf-cli-orchestrator.json`
- `services/dashboard/tests/pacts/dashboard-orchestrator.json`
- `services/agent-runner/tests/pacts/agent-runner-orchestrator.json` (event bus contracts)

### 8.4 E2E Test Scenarios

Playwright-based E2E tests run against a fully composed local environment (`docker-compose up`).

| Scenario | Steps | Acceptance Criteria |
|---|---|---|
| **Full pipeline via dashboard** | 1. Navigate to dashboard. 2. Log in as operator. 3. Click "New Pipeline". 4. Enter idea. 5. Submit. | Pipeline card appears in list; DAG visualization shows stages progressing; PR URL appears on completion |
| **Full pipeline via CLI** | `apf run "build a REST API for a bookstore"` | Terminal shows all 11 stages completing; output includes PR URL |
| **Pipeline failure and retry** | Configure invalid LLM API key; run pipeline; fix key; retry failed stage | Stage retries; pipeline completes |
| **Slack approval gate** | Configure HITL gate on architect stage; run pipeline; receive Slack message; click Approve | Pipeline resumes from architect stage |
| **Jira Epic creation** | Configure Jira connector; run pipeline; check Jira | Epic created with correct title; Stories created after engineering stage |
| **Resume from checkpoint** | Start pipeline; cancel after PRD stage; resume with `--from architect` | Pipeline picks up from architect stage; PRD artifact reused |
| **Dashboard artifact download** | Navigate to completed pipeline; click artifact; download ZIP | ZIP contains all stage artifacts with correct filenames |
| **Auth enforcement** | Access pipeline list without token | 401 response; redirect to login page |

---

## 9. CI/CD Pipeline

### 9.1 GitHub Actions: `ci.yml` (runs on every PR and push to main)

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with: { version: "0.4.x" }
      - run: uv sync --all-packages --dev
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy packages/ services/ cli/ --ignore-missing-imports

  lint-typescript:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - run: pnpm install --frozen-lockfile
      - run: pnpm --filter dashboard run lint
      - run: pnpm --filter dashboard run type-check

  test-python-unit:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --all-packages --dev
      - run: |
          uv run pytest packages/ services/ cli/ \
            -m "not integration and not e2e" \
            --cov=. \
            --cov-report=xml \
            --cov-fail-under=80 \
            -n auto
      - uses: codecov/codecov-action@v4

  test-typescript-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - run: pnpm install --frozen-lockfile
      - run: pnpm --filter dashboard run test --coverage

  test-integration:
    runs-on: ubuntu-latest
    needs: [test-python-unit]
    services:
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: apf_test
        ports: ["5432:5432"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --all-packages --dev
      - run: uv run alembic -c packages/db/alembic.ini upgrade head
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:test@localhost/apf_test
      - run: |
          uv run pytest services/ packages/ \
            -m "integration" \
            --timeout=120 \
            -x
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:test@localhost/apf_test
          REDIS_URL: redis://localhost:6379

  contract-test:
    runs-on: ubuntu-latest
    needs: [test-python-unit]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --all-packages --dev
      - run: uv run pytest cli/tests/pacts/ services/orchestrator/tests/contract/ -m "contract"

  schemathesis:
    runs-on: ubuntu-latest
    needs: [test-integration]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --all-packages --dev
      - name: Start orchestrator for schema testing
        run: docker compose -f deploy/docker-compose.yml up -d orchestrator redis
      - run: uv run schemathesis run http://localhost:8000/api/v1/openapi.json --checks all

  build-docker:
    runs-on: ubuntu-latest
    needs: [lint-python, lint-typescript, test-python-unit, test-typescript-unit]
    strategy:
      matrix:
        service: [orchestrator, agent-runner, artifact-store, github-integration, dashboard, slack-connector, jira-connector, confluence-connector, aws-connector]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - run: docker build -f services/${{ matrix.service }}/Dockerfile . --tag apf/${{ matrix.service }}:ci
```

### 9.2 Quality Gates

All of the following must pass before a PR can be merged (enforced via GitHub branch protection):

| Gate | Tool | Threshold |
|---|---|---|
| Python linting | `ruff check` | Zero violations |
| Python formatting | `ruff format --check` | Zero diffs |
| Python type checking | `mypy` | Zero errors (strict on `packages/`, `services/orchestrator/`, `cli/`) |
| TypeScript linting | `eslint` | Zero errors |
| TypeScript types | `tsc --noEmit` | Zero errors |
| Python unit test coverage | `pytest-cov` | ≥ 80% line coverage across all packages |
| TypeScript unit test coverage | `vitest --coverage` | ≥ 80% line coverage (dashboard) |
| Integration tests | `pytest -m integration` | All pass |
| Contract tests | `pytest -m contract` | All pass |
| Docker builds | `docker build` | Zero build failures for all services |
| Dependency review | GitHub dependency-review-action | No high/critical CVEs introduced |

### 9.3 GitHub Actions: `release.yml` (runs on version tags `v*.*.*`)

```yaml
name: Release

on:
  push:
    tags: ["v*.*.*"]

jobs:
  test-full:
    uses: ./.github/workflows/ci.yml

  publish-images:
    needs: [test-full]
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    strategy:
      matrix:
        service: [orchestrator, agent-runner, artifact-store, github-integration, dashboard, slack-connector, jira-connector, confluence-connector, aws-connector]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/setup-buildx-action@v3
      - uses: docker/metadata-action@v5
        id: meta
        with:
          images: ghcr.io/apf-project/${{ matrix.service }}
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=raw,value=latest,enable=${{ !contains(github.ref_name, '-') }}
      - uses: docker/build-push-action@v5
        with:
          context: .
          file: services/${{ matrix.service }}/Dockerfile
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  publish-cli:
    needs: [test-full]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv build --package apf-cli
      - run: uv publish --token ${{ secrets.PYPI_TOKEN }}

  generate-sbom:
    needs: [publish-images]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: anchore/sbom-action@v0
        with:
          image: ghcr.io/apf-project/orchestrator:${{ github.ref_name }}
          format: spdx-json
          output-file: sbom.spdx.json
      - uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: sbom.spdx.json

  create-release:
    needs: [publish-images, publish-cli, generate-sbom]
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/download-artifact@v4
        with:
          name: sbom
      - uses: softprops/action-gh-release@v2
        with:
          body_path: CHANGELOG.md
          files: sbom.spdx.json
          generate_release_notes: true
```

### 9.4 Docker Build Strategy

**Multi-stage build pattern (all Python services):**

```dockerfile
# Stage 1: builder — resolves and installs dependencies
FROM python:3.12-slim AS builder
WORKDIR /build
RUN pip install uv
COPY pyproject.toml uv.lock ./
COPY packages/ ./packages/
RUN uv sync --no-dev --no-editable

# Stage 2: runtime — minimal image
FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=builder /build/.venv /app/.venv
COPY services/orchestrator/apf_orchestrator ./apf_orchestrator
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8000/healthz || exit 1
ENTRYPOINT ["uvicorn", "apf_orchestrator.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend build pattern:**

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /build
COPY services/dashboard/package.json services/dashboard/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY services/dashboard/ ./
RUN pnpm run build

FROM nginx:1.26-alpine AS runtime
COPY --from=builder /build/dist /usr/share/nginx/html
COPY services/dashboard/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### 9.5 Release Tagging

- Tags follow semantic versioning: `v{MAJOR}.{MINOR}.{PATCH}`
- `MAJOR`: Breaking API changes or pipeline definition schema changes
- `MINOR`: New agents, new connectors, new API endpoints (backward-compatible)
- `PATCH`: Bug fixes, dependency updates, performance improvements
- Pre-release tags: `v1.0.0-alpha.1`, `v1.0.0-beta.2`, `v1.0.0-rc.1`
- The `CHANGELOG.md` is updated by the release workflow using `git-cliff` for conventional commit parsing
- Tags are created only by repository admins via the GitHub release UI; `release.yml` triggers on tag push

---

## 10. Milestones

### Week 1–2: Phase 0 — Foundations

**Deliverables:**
- Repository structure created at `apf/` with all directories scaffolded
- `packages/agent-core/`: `BaseAgent`, all 11 artifact Pydantic schemas, `LLMProvider` protocol, `AnthropicProvider` and `OpenAIProvider` stubs, all 11 Jinja2 prompt templates (placeholder content)
- `packages/db/`: all ORM models, `0001_initial_schema.py` migration, `session.py`, tests pass on SQLite in-memory
- `packages/event-bus/`: `EventBusClient`, all event schemas, Redis connection with `fakeredis` stub for tests
- `deploy/docker-compose.yml`: Redis + PostgreSQL + placeholder service stubs that `docker compose up` starts without error
- `deploy/.env.example` with all required variables documented
- GitHub Actions `ci.yml`: runs `ruff`, `mypy`, `pytest` (empty suites pass), `vitest` (empty suites pass) on every push
- `.pre-commit-config.yaml` installed and validated

**Acceptance criteria:**
- `uv run pytest packages/` exits 0
- `docker compose up` starts Redis and PostgreSQL without errors
- CI `ci.yml` runs to completion (green) on the initial commit

---

### Week 3–4: Phase 1a — Orchestrator Core

**Deliverables:**
- `services/orchestrator/` complete:
  - `PipelineEngine.run()` executes a hardcoded 3-stage DAG (prd → architect → engineering) using the event bus
  - `PipelineDAG.from_yaml()` parses the default pipeline YAML
  - `PipelineScheduler` enforces max-concurrent semaphore
  - `checkpoint.py` saves/loads stage state to SQLite
  - `retry.py` with exponential backoff
  - REST API: `POST /api/v1/pipelines`, `GET /api/v1/pipelines`, `GET /api/v1/pipelines/{id}`, `DELETE /api/v1/pipelines/{id}`, `/healthz`, `/readyz`
  - JWT auth: `POST /api/v1/auth/token`
- Unit tests passing at ≥ 90% coverage for `core/`
- Integration tests: `test_pipelines_api.py` all pass against in-process ASGI client

**Acceptance criteria:**
- `POST /api/v1/pipelines` creates a pipeline record in the DB with `status=queued`
- `GET /api/v1/pipelines/{id}` returns correct status transitions as the engine processes stages
- Max concurrent runs (default: 5) is enforced — 6th concurrent request returns `429`

---

### Week 5–6: Phase 1b — Agent Runner + Artifact Store

**Deliverables:**
- `services/artifact-store/`: local filesystem backend, full CRUD API, ZIP download endpoint
- `services/agent-runner/`: all 11 agents implemented (backed by real LLM calls in manual testing, mocked in unit tests), worker loop consuming from Redis Streams
- `packages/agent-core/` prompts: all 11 `*.j2` templates with production-quality system prompt content
- `services/orchestrator/` WebSocket: `/ws/pipelines/{run_id}` broadcasting stage events
- Full `docker-compose.yml` with all 4 core services: orchestrator, agent-runner, artifact-store, Redis, SQLite volume
- End-to-end smoke test: `docker compose up` + `curl POST /api/v1/pipelines` triggers a real LLM-backed PRD agent run

**Acceptance criteria:**
- A pipeline run initiated via API executes all 11 stages and persists all artifacts
- WebSocket client receives `stage_completed` events for each stage in real time
- All artifacts downloadable via `GET /api/v1/artifacts/{id}/content`
- Agent-runner unit tests: ≥ 85% coverage for all agents

---

### Week 7–8: Phase 2a — GitHub Integration

**Deliverables:**
- `services/github-integration/`: webhook receiver with HMAC validation, branch creation, multi-file commit, PR creation with structured description, review comment posting
- `DeveloperAgent` calls github-integration service to commit generated code to the feature branch
- `ReviewAgent` posts structured review to PR via GitHub Reviews API
- GitHub webhook triggers pipeline from `issues.labeled` event with `apf-build` label
- Branch naming: `apf/{run_id}/{slug}` convention enforced

**Acceptance criteria:**
- Posting a GitHub issue with label `apf-build` triggers a pipeline run
- On pipeline completion, a PR is created on the configured repository
- `ReviewAgent` output appears as inline review comments on the PR
- Webhook signature validation rejects requests with invalid signatures (`401`)

---

### Week 9: Phase 2b — CLI

**Deliverables:**
- `cli/apf_cli/`: all commands implemented against live orchestrator API
- `apf run`, `apf status`, `apf logs`, `apf artifacts`, `apf config init`, `apf auth login`, `apf integrations` all functional
- Rich terminal output with stage progress indicators
- `--json` flag for machine-readable output
- `pip install apf-cli` working on TestPyPI
- CLI unit tests: ≥ 80% coverage
- CLI `apf config init` wizard covers: LLM provider, GitHub integration, storage backend

**Acceptance criteria:**
- `apf run "build a todo REST API"` triggers a full pipeline run and streams stage progress to terminal
- `apf status {run_id}` returns current pipeline status
- `apf logs {run_id} --stage prd` returns PRD agent logs
- `pip install apf-cli` on a clean Python 3.11+ environment installs without errors

---

### Week 10–12: Phase 3 — Web Dashboard

**Deliverables:**
- `services/dashboard/` React app fully functional:
  - Pipeline list view with filter/sort
  - Pipeline detail view with reactflow DAG visualization
  - Real-time stage progress via WebSocket
  - Log viewer with level filtering
  - Artifact viewer with markdown rendering and syntax highlighting
  - Artifact ZIP download
  - Settings page with connector status
  - Login page + JWT authentication
  - AuthGuard protecting all routes
- Playwright E2E tests: all 8 scenarios passing against `docker compose up`
- Dashboard Docker build: `nginx:1.26-alpine` serving the Vite production build
- `docker-compose.yml` updated with dashboard service on port 3000

**Acceptance criteria:**
- Dashboard loads in < 2s with 100 pipeline records in the DB
- Real-time stage updates appear in the DAG within 500ms of the event occurring
- All 8 E2E test scenarios pass in CI
- Dashboard accessible at `http://localhost:3000` after `docker compose up`

---

### Week 13–14: Phase 4a — Slack + Jira Connectors

**Deliverables:**
- `services/slack-connector/`: pipeline notifications (started, stage completed, completed, failed), all 4 slash commands (`/apf run|status|approve|cancel`), interactive approval buttons
- Human-in-the-loop gate: orchestrator pauses pipeline at configured stages and publishes `pipeline.approval_requested` event; Slack connector sends approval message; connector publishes `pipeline.approval_responded` on button click
- `services/jira-connector/`: Epic creation on pipeline start, Story + Task creation after engineering stage, status transitions, PR remote link, artifact attachment
- Connector enable/disable via `PUT /api/v1/connectors/{name}` API
- `apf integrations enable slack|jira` CLI commands functional

**Acceptance criteria:**
- Starting a pipeline posts a Slack notification to the configured channel within 5 seconds
- `/apf approve {run_id}` resumes a paused pipeline
- `/apf cancel {run_id}` cancels a running pipeline
- A Jira Epic is created when the pipeline starts
- Jira Stories are created after the engineering stage completes
- Jira issue status transitions to "In Review" when the GitHub PR is opened

---

### Week 15–16: Phase 4b — Confluence + AWS Connectors

**Deliverables:**
- `services/confluence-connector/`: Markdown → Confluence Storage Format conversion, page upsert with version history, metadata panel, inter-page links (PRD ↔ Architecture ↔ README)
- `services/aws-connector/`: CodePipeline trigger, ECS rolling deploy, Lambda function code update, deployment status polling, rollback on failure, `terraform plan` output to dashboard/Slack
- `apf integrations enable confluence|aws` functional

**Acceptance criteria:**
- On pipeline completion, Confluence pages created for PRD, architecture, README, QA report
- Re-running pipeline updates existing Confluence pages (increments version, does not create duplicate)
- AWS CodePipeline execution triggered after PR merge
- Deployment success/failure reported to dashboard and Slack

---

### Week 17: Phase 4 — Integration Hardening

**Deliverables:**
- All 4 connectors tested against live external services (staging Slack workspace, Jira sandbox, Confluence sandbox, AWS dev account)
- Connector health check (`POST /api/v1/connectors/{name}/test`) implemented for all connectors
- Connector failure isolation: one connector failing does not halt the pipeline or affect other connectors
- Integration tests for all connectors using mock external APIs (respx)
- `apf integrations list` shows real connectivity status for each connector

**Acceptance criteria:**
- All connector integration tests pass in CI using mock external APIs
- A misconfigured Jira connector returns `{ "success": false }` on the test endpoint without affecting pipeline execution
- Pipeline completion notification reaches Slack even when Jira connector is erroring

---

### Week 18–19: Phase 5a — Observability + Security Hardening

**Deliverables:**
- Prometheus `/metrics` endpoint on orchestrator: pipeline starts/min, stage latency P50/P95/P99, agent error rate, queue depth, LLM token consumption
- OpenTelemetry tracing: each pipeline run is a trace; each stage is a span; exported via OTLP
- Structured JSON logging across all services (no unstructured print statements)
- `ReviewAgent` Semgrep integration: runs `semgrep --config auto` on generated code; blocks pipeline on HIGH/CRITICAL findings
- `ReviewAgent` secret scanning: entropy + regex scan on all generated files; blocks on matches
- S3 backend for artifact-store: `boto3`-based, tested with `moto`
- PostgreSQL support validated: all migrations apply cleanly; all integration tests pass against PostgreSQL

**Acceptance criteria:**
- `curl http://localhost:8000/metrics` returns Prometheus-formatted metrics including `apf_pipeline_starts_total`
- A pipeline run containing a fake API key string is blocked by the secret scanner at the review stage
- All integration tests pass against both SQLite and PostgreSQL backends in CI

---

### Week 20: Phase 5b — Documentation + Launch Prep

**Deliverables:**
- `docs/deployment.md`: single-node Docker Compose install in < 5 steps; Helm chart install guide
- `docs/configuration.md`: all `.apf/config.yaml` fields documented with types, defaults, and examples
- `docs/api-reference.md`: generated from OpenAPI spec + hand-written usage examples
- `docs/contributing.md`: dev setup, branching strategy, PR process, test running guide
- `docs/adr/`: all 4 ADRs written
- `README.md`: project overview, quickstart (3 commands to running pipeline), architecture diagram, feature table, link to docs
- `CONTRIBUTING.md` at repo root
- `deploy/.env.example` complete with all variables documented
- Helm chart `helm/apf/` complete with `values.yaml` covering all configuration options
- Load test: Locust scenario simulating 5 concurrent pipeline runs over 10 minutes — all must complete
- `scripts/setup-dev.sh` tested on Ubuntu 22.04, macOS 14, and Windows WSL2
- Final pre-launch checklist: SBOM generated, all CVE scans clean, LICENSE file present, version `v1.0.0` tag created

**Acceptance criteria:**
- A developer with no prior APF knowledge can follow `docs/deployment.md` and have a running pipeline in < 10 minutes
- `docker compose up` on a clean machine (no cached layers) completes successfully and all 6 health checks pass
- Load test: 5 concurrent pipelines (each running 11 mock-LLM stages) complete within 10 minutes with zero errors
- `v1.0.0` tag triggers `release.yml`: all 9 Docker images published to `ghcr.io/apf-project/`, `apf-cli` published to PyPI, GitHub release created with SBOM attached

---

### Summary Timeline

| Weeks | Phase | Key Output |
|---|---|---|
| 1–2 | Phase 0: Foundations | Repo scaffold, shared packages, CI skeleton |
| 3–4 | Phase 1a: Orchestrator Core | Pipeline engine + REST API |
| 5–6 | Phase 1b: Agent Runner + Artifact Store | All 11 agents running, artifacts persisted |
| 7–8 | Phase 2a: GitHub Integration | Real PR creation from pipeline |
| 9 | Phase 2b: CLI | `apf run` end-to-end functional |
| 10–12 | Phase 3: Dashboard | Browser UI with live updates |
| 13–14 | Phase 4a: Slack + Jira | Enterprise connectors #1 and #2 |
| 15–16 | Phase 4b: Confluence + AWS | Enterprise connectors #3 and #4 |
| 17 | Phase 4 Hardening | Connector fault isolation, live E2E |
| 18–19 | Phase 5a: Observability + Security | Metrics, tracing, SAST, secret scan |
| 20 | Phase 5b: Docs + Launch | `v1.0.0` tagged and published |

---

*This engineering plan was authored by the APF Engineering Agent on 2026-03-23, based on PRD v1.0.0 and Market Analysis 2026-03-23. It is the authoritative implementation specification for all developer and build agents in the APF pipeline.*
