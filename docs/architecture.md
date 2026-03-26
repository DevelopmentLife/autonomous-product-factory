# Architecture Document
# Autonomous Product Factory (APF)

**Version:** 1.0.0
**Status:** Approved
**Date:** 2026-03-23
**Owner:** Engineering

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Services](#2-services)
3. [Data Architecture](#3-data-architecture)
4. [LLM Integration](#4-llm-integration)
5. [Authentication & Authorization](#5-authentication--authorization)
6. [Deployment Architecture](#6-deployment-architecture)
7. [Observability](#7-observability)
8. [Sequence Diagrams](#8-sequence-diagrams)
9. [Quality Gates Implementation](#9-quality-gates-implementation)
10. [Extension Points](#10-extension-points)

---

## 1. System Overview

### 1.1 Architecture Diagram

```
                         ┌─────────────────────────────────────────────────────────────────┐
                         │                        APF Platform                              │
                         │                                                                   │
  ┌──────────┐           │  ┌─────────────┐     ┌──────────────┐     ┌──────────────────┐  │
  │  CLI     │──────────▶│  │ api-gateway │────▶│ orchestrator │────▶│  agent-runner    │  │
  └──────────┘           │  │  :8080      │     │  :8081       │     │  :8082           │  │
                         │  └──────┬──────┘     └──────┬───────┘     └────────┬─────────┘  │
  ┌──────────┐           │         │                   │                      │             │
  │ Browser  │──────────▶│  ┌──────▼──────┐           │                      │             │
  └──────────┘           │  │dashboard-ui │            │                      │             │
                         │  │  :3000      │            │             ┌────────▼─────────┐  │
  ┌──────────┐           │  └─────────────┘            │             │  artifact-store  │  │
  │ GitHub   │──────────▶│                             │             │  :8083           │  │
  │ Webhooks │           │  ┌─────────────┐            │             └──────────────────┘  │
  └──────────┘           │  │dashboard-api│◀───────────┤                                   │
                         │  │  :8084      │            │                                   │
  ┌──────────┐           │  └─────────────┘            │                                   │
  │  Slack   │──────────▶│                             │  ┌──────────────────────────────┐ │
  └──────────┘           │                             │  │     Event Bus (Redis Streams) │ │
                         │                             ▼  └──────────────────────────────┘ │
                         │            ┌────────────────────────────────────┐               │
                         │            │           Connectors               │               │
                         │            │  ┌──────────────┐  ┌────────────┐  │               │
                         │            │  │github-connect│  │slack-conn  │  │               │
                         │            │  │  :8085       │  │  :8086     │  │               │
                         │            │  └──────────────┘  └────────────┘  │               │
                         │            │  ┌──────────────┐  ┌────────────┐  │               │
                         │            │  │jira-connector│  │confluence  │  │               │
                         │            │  │  :8087       │  │  :8088     │  │               │
                         │            │  └──────────────┘  └────────────┘  │               │
                         │            │  ┌──────────────┐  ┌────────────┐  │               │
                         │            │  │aws-connector │  │  worker    │  │               │
                         │            │  │  :8089       │  │  :8090     │  │               │
                         │            │  └──────────────┘  └────────────┘  │               │
                         │            └────────────────────────────────────┘               │
                         │                                                                   │
                         │  ┌─────────────────────────────────────────────────────────────┐ │
                         │  │                     Persistence Layer                        │ │
                         │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐ │ │
                         │  │  │PostgreSQL│  │  Redis   │  │   MinIO  │  │  Vault/Env  │ │ │
                         │  │  │(primary) │  │(cache +  │  │(artifacts│  │  (secrets)  │ │ │
                         │  │  │          │  │ streams) │  │  store)  │  │             │ │ │
                         │  │  └──────────┘  └──────────┘  └──────────┘  └─────────────┘ │ │
                         │  └─────────────────────────────────────────────────────────────┘ │
                         └─────────────────────────────────────────────────────────────────┘
```

### 1.2 Design Decisions and Rationale

#### ADR-001: Microservices over Monolith

**Decision:** Implement each logical domain as a separate microservice.

**Context:** APF must support self-hosted single-node deployments for solo developers and horizontally scaled deployments for enterprise teams. The optional integration connectors must be independently deployable and togglable without affecting core pipeline execution.

**Rationale:** A microservices architecture allows: (a) connectors to be omitted from Docker Compose entirely when not needed, reducing resource footprint; (b) individual services to be scaled independently under load (agent-runner is CPU/IO-bound, dashboard-api is read-heavy); (c) fault isolation so a failing Slack connector does not bring down the pipeline; (d) independent deployment cadences per service.

**Trade-off:** Increased operational complexity versus a monolith. Mitigated by Docker Compose for local deployment and a Kubernetes Helm chart for production.

---

#### ADR-002: Redis Streams as the Event Bus

**Decision:** Use Redis Streams as the internal event bus rather than RabbitMQ, Kafka, or NATS.

**Context:** APF must ship a single-node self-hosted option that is easy to install. Adding a separate Kafka cluster is a significant operational burden for solo developers.

**Rationale:** Redis is already required as a distributed cache and session store. Redis Streams provides durable, consumer-group-aware message delivery that satisfies APF's event bus requirements without adding a second message broker. At the scale of APF (hundreds of pipelines per day per installation), Redis Streams throughput is more than sufficient. For enterprise scale, the event bus interface is abstracted so Redis Streams can be replaced with Kafka by swapping the adapter.

---

#### ADR-003: PostgreSQL as Primary Database with SQLite Fallback

**Decision:** PostgreSQL is the production database. SQLite is supported for zero-dependency local development.

**Context:** PRD OQ-2 and Section 7.5 note that solo developers need a simple install with no external DB dependency, while HA deployments require a proper RDBMS.

**Rationale:** The ORM layer (Prisma for Node.js services) supports both PostgreSQL and SQLite dialects. On first run, if `DATABASE_URL` is not set, APF defaults to a local SQLite file at `~/.apf/apf.db`. Production and CI deployments configure PostgreSQL via environment variable.

---

#### ADR-004: MinIO as S3-Compatible Artifact Store

**Decision:** Ship MinIO as a sidecar container for self-hosted installs; use real S3 in production deployments.

**Context:** PRD OQ-3 asks whether to ship a MinIO sidecar or rely on local filesystem. Artifacts can be up to 100 MB each with up to 10 GB per pipeline run.

**Rationale:** MinIO provides an S3-compatible API, so the artifact-store service uses the AWS SDK with a configurable endpoint. In local mode, MinIO runs as a Docker Compose service. In production, `ARTIFACT_STORE_ENDPOINT` is set to the real S3 endpoint. This provides a single code path and avoids maintaining both a filesystem adapter and an S3 adapter.

---

#### ADR-005: Node.js (TypeScript) for All Services Except Agent-Runner

**Decision:** All services are implemented in TypeScript running on Node.js 22 LTS except agent-runner, which is Python 3.12.

**Context:** The agent-runner must integrate with LLM SDKs (Anthropic, OpenAI), prompt management libraries, and code execution tools. The Python ML/AI ecosystem is significantly richer than the Node.js equivalents.

**Rationale:** Node.js provides excellent async I/O performance for API gateway, orchestrator, and connector services. Python is the natural language for agent-runner given Anthropic's and OpenAI's Python SDKs, LangChain, and tooling like tree-sitter for code parsing. The two languages communicate over internal REST/gRPC, not shared memory, so the polyglot boundary is clean.

---

#### ADR-006: REST for External APIs, gRPC for Internal Service Communication

**Decision:** Services expose REST (HTTP/JSON) to external clients (CLI, browser, webhooks). Internal service-to-service calls use gRPC with Protocol Buffers.

**Rationale:** REST is universally supported by CLI tools, browsers, and third-party webhooks. gRPC provides strongly-typed contracts, bidirectional streaming (useful for streaming agent logs), and lower serialization overhead for internal calls. The api-gateway translates external REST to internal gRPC calls.

---

### 1.3 Technology Stack

| Layer | Technology | Version | Justification |
|---|---|---|---|
| Runtime (services) | Node.js | 22 LTS | Long-term support, excellent async I/O, TypeScript support |
| Runtime (agent-runner) | Python | 3.12 | Best-in-class LLM SDK support (Anthropic, OpenAI) |
| Language (services) | TypeScript | 5.x | Type safety, excellent IDE support, matches Node.js ecosystem |
| Language (agent-runner) | Python | 3.12 | Matches ML/AI tooling ecosystem |
| Web Framework (Node.js) | Fastify | 4.x | Highest throughput Node.js framework, schema validation built-in |
| Web Framework (Python) | FastAPI | 0.111 | Async, OpenAPI auto-generation, pydantic validation |
| ORM | Prisma | 5.x | Type-safe, multi-database, migration management |
| Event Bus | Redis Streams | via Redis 7.x | Durable, consumer groups, already in stack |
| Cache / Session | Redis | 7.x | In-memory performance, pub/sub for WebSocket fan-out |
| Primary Database | PostgreSQL | 16 | Battle-tested RDBMS, JSONB for flexible artifact metadata |
| Artifact Store | MinIO / AWS S3 | MinIO RELEASE.2024+ | S3-compatible, self-hostable |
| Internal RPC | gRPC + Protobuf | grpc 1.x | Strongly typed, streaming, efficient binary serialization |
| Frontend | React | 18.x | Industry standard, large ecosystem |
| Frontend Build | Vite | 5.x | Fast HMR, modern ESM bundling |
| Frontend State | Zustand | 4.x | Minimal boilerplate, sufficient for dashboard scale |
| Frontend Real-time | Native WebSocket | — | Avoids Socket.io overhead; dashboard-api manages rooms |
| Container Runtime | Docker | 26.x | Universal container standard |
| Orchestration (prod) | Kubernetes | 1.30 | Standard for HA deployments |
| Secret Management | HashiCorp Vault / AWS Secrets Manager / Env vars | — | Three-tier: Vault (enterprise), ASM (AWS), env vars (dev) |
| Observability | OpenTelemetry + Prometheus + Grafana | — | Standard, vendor-neutral observability stack |
| CI/CD | GitHub Actions | — | Native GitHub integration, no external CI service needed |

---

## 2. Services

### 2.1 api-gateway

**Responsibility:** Single entry point for all external traffic. Handles authentication token validation, API key verification, rate limiting, request routing, and TLS termination. Translates external REST calls to internal gRPC.

**Language/Runtime:** TypeScript / Node.js 22

**Public API (REST :8080)**

| Method | Path | Description |
|---|---|---|
| POST | `/v1/auth/login` | Username/password login, returns JWT |
| POST | `/v1/auth/refresh` | Refresh JWT using refresh token |
| DELETE | `/v1/auth/logout` | Invalidate refresh token |
| POST | `/v1/pipelines` | Trigger a new pipeline run |
| GET | `/v1/pipelines` | List pipeline runs (paginated) |
| GET | `/v1/pipelines/:runId` | Get pipeline run detail |
| DELETE | `/v1/pipelines/:runId` | Cancel a running pipeline |
| GET | `/v1/pipelines/:runId/logs` | Stream or retrieve logs (SSE) |
| GET | `/v1/pipelines/:runId/artifacts` | List artifacts for a run |
| GET | `/v1/artifacts/:artifactId` | Download a specific artifact |
| GET | `/v1/config` | Get current APF configuration |
| PUT | `/v1/config` | Update APF configuration (admin) |
| GET | `/v1/integrations` | List integrations and their status |
| PUT | `/v1/integrations/:name` | Enable/disable an integration |
| POST | `/v1/webhooks/github` | Receive GitHub webhook events |
| POST | `/v1/webhooks/slack` | Receive Slack event payloads |
| GET | `/healthz` | Liveness probe |
| GET | `/readyz` | Readiness probe |
| GET | `/metrics` | Prometheus metrics |

**Internal Events Emitted:**
- `pipeline.trigger_requested` — downstream: orchestrator

**Internal Events Consumed:**
- None (gateway is a synchronous proxy; async events originate from orchestrator)

**Data Owned:**
- JWT refresh tokens (Redis, TTL-based)
- Rate limit counters (Redis)
- API key records (shared read from `users` table in PostgreSQL; owned by auth subsystem within this service)

**Dependencies:**
- Redis (session / rate limiting)
- PostgreSQL (API key and user lookup)
- orchestrator (gRPC: trigger, cancel, status)
- artifact-store (gRPC: list, download)
- dashboard-api (reverse-proxy for `/app/*` routes)

---

### 2.2 orchestrator

**Responsibility:** Core pipeline runtime. Loads pipeline DAG definitions, sequences stages, evaluates quality gates, manages retries, maintains pipeline state, and emits lifecycle events to the event bus.

**Language/Runtime:** TypeScript / Node.js 22

**Internal gRPC API (:8081)**

```protobuf
service Orchestrator {
  rpc TriggerPipeline(TriggerRequest) returns (TriggerResponse);
  rpc CancelPipeline(CancelRequest) returns (CancelResponse);
  rpc GetPipelineStatus(StatusRequest) returns (StatusResponse);
  rpc ApprovePipelineGate(ApproveRequest) returns (ApproveResponse);
  rpc StreamPipelineLogs(LogStreamRequest) returns (stream LogEntry);
}
```

**Internal Events Emitted** (to Redis Streams):

| Stream | Event | Description |
|---|---|---|
| `apf:pipeline` | `pipeline.started` | Pipeline execution began |
| `apf:pipeline` | `pipeline.stage.started` | A stage began executing |
| `apf:pipeline` | `pipeline.stage.completed` | A stage completed successfully |
| `apf:pipeline` | `pipeline.stage.failed` | A stage failed (with retry info) |
| `apf:pipeline` | `pipeline.gate.pending` | HITL gate is waiting for approval |
| `apf:pipeline` | `pipeline.gate.approved` | HITL gate was approved |
| `apf:pipeline` | `pipeline.gate.rejected` | HITL gate was rejected |
| `apf:pipeline` | `pipeline.completed` | All stages completed |
| `apf:pipeline` | `pipeline.failed` | Pipeline halted with unrecoverable error |
| `apf:pipeline` | `pipeline.cancelled` | Pipeline was cancelled by user |

**Internal Events Consumed:**

| Stream | Event | Action |
|---|---|---|
| `apf:agent` | `agent_run.completed` | Advance pipeline to next stage |
| `apf:agent` | `agent_run.failed` | Trigger retry or halt pipeline |

**Data Owned:**
- `pipelines` table — pipeline run records
- `stages` table — per-stage execution records
- `quality_gates` table — gate definitions and approval records
- Pipeline DAG definition YAML (loaded from config; not stored in DB)

**Dependencies:**
- PostgreSQL
- Redis Streams
- agent-runner (gRPC: submit agent job)
- artifact-store (gRPC: validate artifact, register artifact)

---

### 2.3 agent-runner

**Responsibility:** Executes individual agent stages. Manages LLM prompt construction, context assembly, streaming LLM API calls, response parsing, artifact schema validation, and retry logic. Isolated from pipeline state.

**Language/Runtime:** Python 3.12

**Internal gRPC API (:8082)**

```protobuf
service AgentRunner {
  rpc SubmitAgentJob(AgentJobRequest) returns (AgentJobResponse);
  rpc CancelAgentJob(CancelJobRequest) returns (CancelJobResponse);
  rpc StreamAgentLogs(LogStreamRequest) returns (stream AgentLogEntry);
  rpc GetAgentJobStatus(JobStatusRequest) returns (JobStatusResponse);
}
```

**Internal Events Emitted** (to Redis Streams):

| Stream | Event | Description |
|---|---|---|
| `apf:agent` | `agent_run.started` | LLM call initiated |
| `apf:agent` | `agent_run.token_chunk` | Streaming token chunk (for live log display) |
| `apf:agent` | `agent_run.completed` | Agent produced a valid artifact |
| `apf:agent` | `agent_run.failed` | Agent failed after all retries |
| `apf:agent` | `agent_run.cost_recorded` | Token usage and cost for billing/tracking |

**Internal Events Consumed:** None (jobs submitted via gRPC from orchestrator)

**Data Owned:**
- `agent_runs` table — per-execution records with token counts, cost, model used, duration
- Prompt templates (filesystem, loaded at startup from `prompts/` directory)
- Provider configuration (loaded from environment / Vault)

**Dependencies:**
- PostgreSQL (write agent_run records)
- Redis Streams (emit events)
- artifact-store (gRPC: upload produced artifacts)
- External LLM APIs (Anthropic, OpenAI, Ollama — via provider abstraction layer)

---

### 2.4 artifact-store

**Responsibility:** Stores, versions, and serves all pipeline artifacts. Provides content-addressed storage with metadata indexing. Enforces artifact schema validation.

**Language/Runtime:** TypeScript / Node.js 22

**Internal gRPC API (:8083)**

```protobuf
service ArtifactStore {
  rpc UploadArtifact(stream ArtifactChunk) returns (ArtifactMetadata);
  rpc DownloadArtifact(ArtifactRequest) returns (stream ArtifactChunk);
  rpc GetArtifactMetadata(ArtifactRequest) returns (ArtifactMetadata);
  rpc ListArtifacts(ListRequest) returns (ArtifactList);
  rpc ValidateArtifact(ValidateRequest) returns (ValidationResult);
  rpc DeleteRunArtifacts(DeleteRequest) returns (DeleteResponse);
}
```

**Internal Events Emitted:**
- `apf:artifacts` — `artifact.uploaded`, `artifact.validated`, `artifact.validation_failed`

**Internal Events Consumed:** None (called directly via gRPC)

**Data Owned:**
- `artifacts` table — metadata: run_id, stage, type, schema_version, content_hash (SHA-256), size, storage_path, created_at
- Binary artifact blobs (MinIO / S3)
- JSON Schema definitions for each artifact type (filesystem, versioned with service)

**Dependencies:**
- PostgreSQL (artifact metadata)
- MinIO / S3 (blob storage via AWS SDK, configurable endpoint)

---

### 2.5 github-connector

**Responsibility:** Wraps the GitHub REST API and GraphQL API. Manages branch creation, file commits, PR creation/update, review comment posting, webhook validation, and GitHub App authentication.

**Language/Runtime:** TypeScript / Node.js 22

**Internal gRPC API (:8085)**

```protobuf
service GitHubConnector {
  rpc CreateBranch(CreateBranchRequest) returns (BranchResponse);
  rpc CommitFiles(CommitFilesRequest) returns (CommitResponse);
  rpc CreatePullRequest(CreatePRRequest) returns (PRResponse);
  rpc UpdatePullRequest(UpdatePRRequest) returns (PRResponse);
  rpc PostReviewComment(ReviewCommentRequest) returns (CommentResponse);
  rpc SubmitReview(SubmitReviewRequest) returns (ReviewResponse);
  rpc GetRepository(RepoRequest) returns (RepoResponse);
  rpc ListBranches(ListBranchesRequest) returns (BranchList);
  rpc ValidateWebhookSignature(WebhookRequest) returns (ValidationResponse);
  rpc GetInstallationToken(TokenRequest) returns (TokenResponse);
}
```

**Internal Events Emitted** (to Redis Streams):

| Stream | Event | Description |
|---|---|---|
| `apf:github` | `github.pr.opened` | PR was created |
| `apf:github` | `github.pr.merged` | PR merge detected via webhook |
| `apf:github` | `github.issue.labeled` | Issue labeled `apf-build` — triggers pipeline |

**Internal Events Consumed:**
- `apf:pipeline` — `pipeline.completed` → create PR
- `apf:agent` — `agent_run.completed` (review stage) → post review comments

**Data Owned:**
- `connector_configs` table (github rows): installation_id, app_id, private_key_ref, owner, repo
- `github_prs` table: run_id, pr_number, pr_url, branch_name, status

**Dependencies:**
- PostgreSQL
- Redis Streams
- Vault / AWS Secrets Manager (GitHub App private key)
- GitHub API (external)

---

### 2.6 slack-connector

**Responsibility:** Slack Bot integration. Sends pipeline notifications, manages interactive message buttons, processes slash commands, and implements the HITL approval flow via Slack.

**Language/Runtime:** TypeScript / Node.js 22

**Internal gRPC API (:8086)**

```protobuf
service SlackConnector {
  rpc SendNotification(SlackNotificationRequest) returns (SlackResponse);
  rpc SendApprovalRequest(ApprovalRequest) returns (SlackResponse);
  rpc UpdateMessage(UpdateMessageRequest) returns (SlackResponse);
  rpc PostThreadReply(ThreadReplyRequest) returns (SlackResponse);
}
```

**Internal Events Emitted** (to Redis Streams):

| Stream | Event | Description |
|---|---|---|
| `apf:slack` | `slack.approval.approved` | User clicked Approve button |
| `apf:slack` | `slack.approval.rejected` | User clicked Reject button |
| `apf:slack` | `slack.command.run` | `/apf run` received |
| `apf:slack` | `slack.command.cancel` | `/apf cancel` received |

**Internal Events Consumed:**
- `apf:pipeline` — all pipeline lifecycle events (for notifications)
- `apf:pipeline` — `pipeline.gate.pending` → send approval request message

**Data Owned:**
- `connector_configs` table (slack rows): bot_token_ref, signing_secret_ref, channel_id mappings
- `slack_messages` table: run_id, channel, ts (message timestamp for threading)

**Dependencies:**
- PostgreSQL
- Redis Streams
- Vault / secrets backend (Slack bot token, signing secret)
- Slack API (external)

---

### 2.7 jira-connector

**Responsibility:** Jira Cloud/Server integration. Creates Epics, Stories, and Tasks from pipeline artifacts, links PRs to issues, transitions issue statuses, and attaches artifacts to Jira issues.

**Language/Runtime:** TypeScript / Node.js 22

**Internal gRPC API (:8087)**

```protobuf
service JiraConnector {
  rpc CreateEpic(CreateEpicRequest) returns (JiraIssueResponse);
  rpc CreateIssue(CreateIssueRequest) returns (JiraIssueResponse);
  rpc UpdateIssueStatus(TransitionRequest) returns (JiraIssueResponse);
  rpc AddRemoteLink(RemoteLinkRequest) returns (RemoteLinkResponse);
  rpc AttachFile(AttachFileRequest) returns (AttachmentResponse);
  rpc GetIssue(GetIssueRequest) returns (JiraIssueResponse);
}
```

**Internal Events Emitted:**
- `apf:jira` — `jira.epic.created`, `jira.issue.created`, `jira.issue.transitioned`

**Internal Events Consumed:**
- `apf:pipeline` — `pipeline.started` → create Epic
- `apf:pipeline` — `pipeline.stage.completed` (engineering stage) → create Stories/Tasks
- `apf:github` — `github.pr.opened` → add remote link, transition to "In Review"
- `apf:github` — `github.pr.merged` → transition to "Done"

**Data Owned:**
- `connector_configs` table (jira rows): base_url, api_token_ref, project_key, issue_type_map
- `jira_issues` table: run_id, jira_key, issue_type, external_id

**Dependencies:**
- PostgreSQL
- Redis Streams
- Vault / secrets backend
- Jira REST API (external)

---

### 2.8 confluence-connector

**Responsibility:** Confluence Cloud/Server integration. Converts markdown artifacts to Confluence Storage Format and creates or updates Confluence pages in the configured space.

**Language/Runtime:** TypeScript / Node.js 22

**Internal gRPC API (:8088)**

```protobuf
service ConfluenceConnector {
  rpc CreateOrUpdatePage(PageRequest) returns (PageResponse);
  rpc GetPage(GetPageRequest) returns (PageResponse);
  rpc AttachFile(AttachRequest) returns (AttachResponse);
  rpc ConvertMarkdown(ConvertRequest) returns (ConvertResponse);
}
```

**Internal Events Emitted:**
- `apf:confluence` — `confluence.page.created`, `confluence.page.updated`

**Internal Events Consumed:**
- `apf:pipeline` — `pipeline.completed` → publish PRD, architecture, README, QA report pages

**Data Owned:**
- `connector_configs` table (confluence rows): base_url, api_token_ref, space_key, parent_page_id
- `confluence_pages` table: run_id, artifact_type, page_id, page_url, page_version

**Dependencies:**
- PostgreSQL
- Redis Streams
- artifact-store (fetch artifact content for publishing)
- Vault / secrets backend
- Confluence REST API (external)

---

### 2.9 aws-connector

**Responsibility:** AWS deployment integration. Triggers CodePipeline executions, ECS service updates, and Lambda deployments. Optionally runs Terraform plan/apply. Monitors deployment status and reports back.

**Language/Runtime:** TypeScript / Node.js 22

**Internal gRPC API (:8089)**

```protobuf
service AWSConnector {
  rpc TriggerDeployment(DeployRequest) returns (DeployResponse);
  rpc GetDeploymentStatus(StatusRequest) returns (DeploymentStatus);
  rpc TriggerRollback(RollbackRequest) returns (RollbackResponse);
  rpc RunTerraformPlan(TerraformRequest) returns (TerraformPlanResponse);
  rpc RunTerraformApply(TerraformApplyRequest) returns (TerraformApplyResponse);
}
```

**Internal Events Emitted:**
- `apf:aws` — `aws.deployment.triggered`, `aws.deployment.succeeded`, `aws.deployment.failed`, `aws.rollback.triggered`

**Internal Events Consumed:**
- `apf:github` — `github.pr.merged` → trigger deployment (configurable)
- `apf:pipeline` — `pipeline.completed` → optionally trigger deployment

**Data Owned:**
- `connector_configs` table (aws rows): region, role_arn_ref, deployment_target_type, target_name
- `aws_deployments` table: run_id, deployment_id, target, status, started_at, completed_at

**Dependencies:**
- PostgreSQL
- Redis Streams
- artifact-store (fetch deployment artifacts produced by DevOps agent)
- Vault / secrets backend (AWS credentials or role ARN)
- AWS SDK (external)

---

### 2.10 dashboard-api

**Responsibility:** Backend-for-Frontend (BFF) for the web dashboard. Aggregates data from orchestrator, artifact-store, and all connectors into dashboard-optimized response shapes. Manages WebSocket connections for real-time pipeline updates.

**Language/Runtime:** TypeScript / Node.js 22

**Public HTTP/WS API (:8084)**

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/pipelines` | Paginated pipeline list with filter/sort |
| GET | `/api/v1/pipelines/:runId` | Pipeline detail with stage timeline |
| GET | `/api/v1/pipelines/:runId/stages` | Stage list with metrics |
| GET | `/api/v1/pipelines/:runId/artifacts` | Artifact list with metadata |
| GET | `/api/v1/artifacts/:id/content` | Rendered artifact content |
| GET | `/api/v1/metrics/summary` | Dashboard summary metrics |
| GET | `/api/v1/integrations` | Integration status per connector |
| GET | `/api/v1/settings` | Current configuration |
| PUT | `/api/v1/settings` | Update configuration |
| GET | `/api/v1/users` | User list (admin) |
| POST | `/api/v1/users` | Create user (admin) |
| WS | `/ws/pipelines/:runId` | Real-time pipeline stage updates |

**Internal Events Consumed** (via Redis pub/sub for WebSocket fan-out):
- All `apf:pipeline` events → broadcast to subscribed WebSocket clients

**Data Owned:** None. Reads from orchestrator DB (shared read replica) and proxies artifact-store.

**Dependencies:**
- PostgreSQL (read replica or same DB with read queries)
- Redis (pub/sub for WebSocket fan-out)
- artifact-store (gRPC: content retrieval)
- orchestrator (gRPC: approve gate action from dashboard)

---

### 2.11 dashboard-ui

**Responsibility:** React single-page application. Provides the full web dashboard: pipeline list, pipeline detail/DAG view, artifact viewer, log viewer, settings, and integration management.

**Language/Runtime:** TypeScript / React 18 / Vite 5

**Served as:** Static assets from `/app` path on api-gateway (nginx in production, Vite dev server locally)

**Key Pages:**

| Route | Description |
|---|---|
| `/` | Pipeline list with filter/sort |
| `/pipelines/:runId` | Pipeline detail — DAG, stages, live status |
| `/pipelines/:runId/artifacts` | Artifact viewer |
| `/pipelines/:runId/logs/:stage` | Stage log viewer |
| `/settings` | Configuration UI |
| `/settings/integrations` | Integration health and configuration |
| `/settings/users` | User management (admin) |

**Technology choices:**
- React 18 with concurrent features for progressive rendering
- Zustand for global state (pipeline list, active run)
- TanStack Query (React Query) for server state and cache management
- Native WebSocket client for real-time DAG updates
- React Syntax Highlighter for code artifact display
- `marked` + DOMPurify for safe markdown rendering
- Tailwind CSS for styling (utility-first, no design system dependency)
- Radix UI for accessible headless components

**Dependencies:**
- dashboard-api (all data via REST + WebSocket)

---

### 2.12 worker

**Responsibility:** Background job processor for long-running, non-latency-sensitive tasks. Handles: artifact ZIP archival, Confluence markdown conversion, stale branch cleanup notifications, pipeline retention policy enforcement, and any deferred connector actions.

**Language/Runtime:** TypeScript / Node.js 22

**No external API.** Jobs are submitted via Redis Streams and processed from consumer group `apf:workers`.

**Job Types:**

| Job | Description |
|---|---|
| `artifact.archive` | ZIP all artifacts for a completed run |
| `branch.cleanup_check` | Flag stale APF branches (TTL-based) |
| `pipeline.retention` | Delete pipeline records older than retention policy |
| `confluence.publish` | Async Confluence page creation (delegated from connector for large docs) |
| `report.generate` | Generate aggregate reports for dashboard metrics |

**Internal Events Consumed:**
- `apf:pipeline` — `pipeline.completed` → enqueue `artifact.archive`
- Cron triggers via Redis Streams scheduled messages

**Data Owned:** None. Mutates records owned by orchestrator and connectors.

**Dependencies:**
- PostgreSQL
- Redis Streams
- artifact-store (gRPC)
- All connectors (gRPC) for delegated tasks

---

## 3. Data Architecture

### 3.1 Database Per Service

| Service | Database | Justification |
|---|---|---|
| api-gateway | PostgreSQL (shared) + Redis | User/API key table; Redis for rate limits and sessions |
| orchestrator | PostgreSQL (owner) | Pipelines, stages, gates — relational, transactional |
| agent-runner | PostgreSQL (owner) | Agent run records with JSONB for token/cost metadata |
| artifact-store | PostgreSQL (owner) + MinIO/S3 | Metadata in PG; blobs in object store |
| github-connector | PostgreSQL (owner) | Connector config, PR records |
| slack-connector | PostgreSQL (owner) | Connector config, message thread IDs |
| jira-connector | PostgreSQL (owner) | Connector config, issue mappings |
| confluence-connector | PostgreSQL (owner) | Connector config, page mappings |
| aws-connector | PostgreSQL (owner) | Connector config, deployment records |
| dashboard-api | PostgreSQL (read) | Read queries only; no owned tables |
| worker | PostgreSQL (read/write for cleanup tasks) | Accesses orchestrator-owned tables under contract |

**Note on database sharing:** All PostgreSQL services connect to the same PostgreSQL instance in the default self-hosted deployment but use separate schemas (e.g., `orchestrator`, `agent_runner`, `artifact_store`). In production, separate database instances per service are recommended. The Prisma client for each service is scoped to its schema only.

### 3.2 Event Bus Design (Redis Streams)

**Stream topology:**

```
apf:pipeline    — pipeline and stage lifecycle events
apf:agent       — agent job events (start, chunk, complete, fail)
apf:artifacts   — artifact upload, validation events
apf:github      — GitHub webhook-derived events
apf:slack       — Slack command and interaction events
apf:jira        — Jira operation events
apf:confluence  — Confluence operation events
apf:aws         — AWS deployment events
apf:workers     — Background job queue
```

**Consumer groups:**

Each service that consumes a stream registers a consumer group with its service name. Messages are acknowledged (`XACK`) only after successful processing. Unacknowledged messages are redelivered after a configurable `XCLAIM` timeout (default: 30 seconds).

**Retention:** All streams use `MAXLEN ~10000` (approximately trimmed) to bound memory usage. For durable audit history, the orchestrator writes all consumed events to the `event_log` PostgreSQL table.

**Message envelope schema:**

```json
{
  "id": "stream-auto-id",
  "type": "pipeline.stage.completed",
  "source": "orchestrator",
  "run_id": "run_01HZ...",
  "stage": "architect",
  "timestamp": "2026-03-23T14:22:01.000Z",
  "correlation_id": "trace-id-xyz",
  "payload": { ... }
}
```

### 3.3 Artifact Storage

**Storage backend:** MinIO (self-hosted) or AWS S3 (production)

**Bucket structure:**

```
apf-artifacts/
  {run_id}/
    {stage_name}/
      {artifact_type}.{ext}        # e.g., prd.md, architecture.md
      {artifact_type}.meta.json    # Schema version, hash, size
  {run_id}/
    archive.zip                    # Generated by worker post-completion
```

**Content addressing:** Each artifact is hashed (SHA-256) on upload. The hash is stored in PostgreSQL. Duplicate blobs within a run are deduplicated by checking hash before uploading.

**Access control:** MinIO bucket policy restricts access to service accounts only. No public access. Pre-signed URLs (15-minute TTL) are used for dashboard artifact downloads.

### 3.4 Key Entity Schemas

#### Pipeline

```sql
CREATE TABLE orchestrator.pipelines (
  id            VARCHAR(26) PRIMARY KEY,  -- ULID
  idea_prompt   TEXT NOT NULL,
  idea_slug     VARCHAR(255) NOT NULL,
  status        VARCHAR(32) NOT NULL,     -- pending | running | completed | failed | cancelled
  pipeline_def  JSONB NOT NULL,           -- snapshot of DAG definition at run time
  config        JSONB NOT NULL,           -- run-time configuration snapshot
  triggered_by  VARCHAR(32) NOT NULL,     -- user_id or "webhook" or "cli"
  github_branch VARCHAR(255),
  github_pr_url VARCHAR(512),
  started_at    TIMESTAMPTZ,
  completed_at  TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### Stage

```sql
CREATE TABLE orchestrator.stages (
  id            VARCHAR(26) PRIMARY KEY,  -- ULID
  run_id        VARCHAR(26) NOT NULL REFERENCES orchestrator.pipelines(id),
  stage_name    VARCHAR(64) NOT NULL,     -- prd | architect | market | ux | engineering | developer | qa | regression | review | devops | readme
  status        VARCHAR(32) NOT NULL,     -- pending | running | completed | failed | skipped
  attempt       INTEGER NOT NULL DEFAULT 1,
  max_attempts  INTEGER NOT NULL DEFAULT 3,
  agent_run_id  VARCHAR(26),             -- FK to agent_runs
  quality_gate_result JSONB,
  error_message TEXT,
  started_at    TIMESTAMPTZ,
  completed_at  TIMESTAMPTZ,
  duration_ms   INTEGER,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### Artifact

```sql
CREATE TABLE artifact_store.artifacts (
  id             VARCHAR(26) PRIMARY KEY,  -- ULID
  run_id         VARCHAR(26) NOT NULL,
  stage_name     VARCHAR(64) NOT NULL,
  artifact_type  VARCHAR(64) NOT NULL,     -- prd | architecture | ux_spec | engineering_plan | source_code | qa_report | etc.
  filename       VARCHAR(512) NOT NULL,
  content_type   VARCHAR(128) NOT NULL,
  schema_version VARCHAR(16) NOT NULL,
  content_hash   CHAR(64) NOT NULL,        -- SHA-256 hex
  size_bytes     BIGINT NOT NULL,
  storage_path   TEXT NOT NULL,            -- s3://bucket/run_id/stage/filename
  validation_status VARCHAR(32) NOT NULL,  -- pending | valid | invalid
  validation_errors JSONB,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### AgentRun

```sql
CREATE TABLE agent_runner.agent_runs (
  id              VARCHAR(26) PRIMARY KEY,  -- ULID
  run_id          VARCHAR(26) NOT NULL,
  stage_name      VARCHAR(64) NOT NULL,
  provider        VARCHAR(32) NOT NULL,     -- anthropic | openai | ollama
  model           VARCHAR(128) NOT NULL,
  prompt_template VARCHAR(128) NOT NULL,    -- name of the template used
  prompt_version  VARCHAR(16) NOT NULL,
  input_tokens    INTEGER,
  output_tokens   INTEGER,
  cost_usd        NUMERIC(10, 6),
  latency_ms      INTEGER,
  status          VARCHAR(32) NOT NULL,     -- running | completed | failed | cancelled
  error_code      VARCHAR(64),
  error_message   TEXT,
  started_at      TIMESTAMPTZ,
  completed_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### ConnectorConfig

```sql
CREATE TABLE connector_store.connector_configs (
  id             VARCHAR(26) PRIMARY KEY,  -- ULID
  connector_name VARCHAR(32) NOT NULL,     -- github | slack | jira | confluence | aws
  enabled        BOOLEAN NOT NULL DEFAULT FALSE,
  config         JSONB NOT NULL,           -- connector-specific non-secret config
  secret_refs    JSONB NOT NULL,           -- references to secret keys (never values)
  health_status  VARCHAR(32) NOT NULL DEFAULT 'unknown',
  last_health_check TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(connector_name)
);
```

---

## 4. LLM Integration

### 4.1 Provider Abstraction Layer

The agent-runner implements a provider abstraction so that agents are decoupled from specific LLM APIs. The abstraction is defined as a Python abstract base class:

```python
class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        system: str,
        max_tokens: int,
        temperature: float,
        stream: bool,
    ) -> AsyncIterator[str] | CompletionResponse: ...

    @abstractmethod
    async def count_tokens(self, text: str) -> int: ...

    @abstractmethod
    def get_context_window(self) -> int: ...

    @abstractmethod
    def get_cost_per_token(self) -> CostConfig: ...
```

**Implemented providers:**

| Provider | Class | Notes |
|---|---|---|
| Anthropic | `AnthropicProvider` | Uses `anthropic` Python SDK; supports streaming |
| OpenAI | `OpenAIProvider` | Uses `openai` Python SDK; also covers Azure OpenAI |
| Ollama | `OllamaProvider` | HTTP calls to local Ollama instance; no token costs |
| OpenAI-compatible | `OpenAICompatibleProvider` | Configurable base URL; covers LM Studio, vLLM, etc. |

Provider selection is per-agent-stage via configuration:

```yaml
# .apf/config.yaml
llm:
  default_provider: anthropic
  default_model: claude-sonnet-4-5
  stage_overrides:
    market:
      provider: openai
      model: gpt-4o
    regression:
      provider: ollama
      model: codestral
```

### 4.2 Prompt Management

Prompts are stored as Jinja2 template files in the `agent-runner` service under `prompts/{stage_name}/v{version}/`:

```
prompts/
  prd/
    v1/
      system.j2         # System prompt
      user.j2           # User message template
      schema.json       # Expected output JSON schema
  architect/
    v1/
      system.j2
      user.j2
      schema.json
  ...
```

**Prompt versioning:** Each prompt has a semantic version. Agent runs record the prompt name and version in `agent_runs.prompt_version`. When prompts are updated, old versions are preserved for reproducibility.

**Template variables:** Jinja2 templates receive a `context` object containing: `idea_prompt`, `artifacts` dict (keyed by stage name), `pipeline_config`, `run_id`, and `current_date`.

### 4.3 Context Window Strategy

Large artifacts (architecture docs, generated code) can exceed model context windows. The agent-runner implements a tiered context strategy:

**Tier 1 — Full context (< 80% of context window):** All prior-stage artifacts are included verbatim.

**Tier 2 — Summarized context (80%–95% of window):** Artifacts from non-essential prior stages are replaced with a structured summary (first 500 tokens + section headings extracted via regex). Essential artifacts (direct inputs defined in the pipeline DAG) remain verbatim.

**Tier 3 — Chunked processing (> 95% of window or source code > 50k tokens):**
- For the developer agent: code is processed file-by-file in separate LLM calls; a synthesis call assembles the final commit.
- For the review agent: diff is chunked by file; reviews are aggregated and de-duplicated.
- For the readme agent: architecture and engineering plan are summarized before inclusion.

The context budget calculator runs before every LLM call and selects the appropriate tier automatically. The selected tier is logged in the `agent_runs` record.

### 4.4 Cost Tracking

The `agent_runs` table records `input_tokens`, `output_tokens`, and `cost_usd` for every LLM call. Cost is calculated using the provider's per-token pricing stored in the provider configuration:

```python
cost_usd = (input_tokens * cost_config.input_per_token) + \
           (output_tokens * cost_config.output_per_token)
```

The dashboard-api aggregates costs per pipeline run and exposes them in the pipeline detail view. A Prometheus gauge `apf_llm_cost_usd_total` (labeled by provider, model, stage) enables cost alerting.

---

## 5. Authentication & Authorization

### 5.1 Auth Strategy

**External (CLI and Browser):**
- **JWT (JSON Web Tokens):** Short-lived access tokens (15 minutes TTL), long-lived refresh tokens (30 days TTL, stored in Redis with hash for rotation).
- **API Keys:** Static keys for programmatic access (CI pipelines, service accounts). Stored as bcrypt hashes in the `api_keys` table. Passed via `Authorization: Bearer <key>` header.
- **OAuth / OIDC (optional):** For enterprise SSO, the api-gateway supports OIDC-compliant identity providers (Google, Okta, Azure AD). Configured via `auth.oidc` in `config.yaml`.

**Internal (service-to-service):**
- **mTLS:** All internal gRPC calls are secured with mutual TLS. Each service has a certificate issued by the APF internal CA (auto-generated on first deployment by a startup script; managed via cert-manager in Kubernetes).
- **Service identity:** gRPC calls include a `x-service-id` header signed with the calling service's private key. The receiving service validates this header to prevent impersonation.

### 5.2 RBAC Model

| Role | Permissions |
|---|---|
| `viewer` | Read pipelines, read artifacts, view logs, view dashboard |
| `operator` | All viewer permissions + trigger pipelines, cancel pipelines, approve HITL gates |
| `admin` | All operator permissions + manage users, manage integrations, modify configuration |

RBAC enforcement is applied at the api-gateway for external routes. Internal gRPC calls between services are not subject to user RBAC (service identity is used instead).

Role assignments are stored in the `user_roles` table. Role checks use a simple enum-ordered model: admin > operator > viewer.

### 5.3 Connector Credential Storage

All connector credentials (GitHub App private key, Slack bot token, Jira API token, Confluence API token, AWS access key) are stored externally, never in the APF database.

**Three-tier secrets strategy:**

| Tier | Backend | Use Case |
|---|---|---|
| Tier 1 | HashiCorp Vault | Enterprise self-hosted deployments with existing Vault |
| Tier 2 | AWS Secrets Manager | APF deployed on AWS |
| Tier 3 | Environment variables | Local development; secrets injected at container start |

The `ConnectorConfig.secret_refs` JSONB column stores only the secret path/key reference (e.g., `vault://secret/apf/github/private_key` or `env://GITHUB_APP_PRIVATE_KEY`), never the secret value.

The connector services resolve secret references at startup and cache decrypted values in memory. Secrets are never written to logs or emitted in events.

---

## 6. Deployment Architecture

### 6.1 Docker Compose (Self-Hosted / Local)

`docker-compose.yml` defines all services as a single-node deployment. Services not enabled in configuration are given a `profiles` label so they can be excluded with `--profile`:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    volumes: [postgres_data:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes

  minio:
    image: minio/minio:latest
    command: server /data --console-address :9001

  api-gateway:
    build: ./services/api-gateway
    ports: ["8080:8080"]
    depends_on: [postgres, redis]

  orchestrator:
    build: ./services/orchestrator
    depends_on: [postgres, redis]

  agent-runner:
    build: ./services/agent-runner
    depends_on: [postgres, redis, artifact-store]

  artifact-store:
    build: ./services/artifact-store
    depends_on: [postgres, minio]

  github-connector:
    build: ./services/github-connector
    profiles: [github]
    depends_on: [postgres, redis]

  slack-connector:
    build: ./services/slack-connector
    profiles: [slack]
    depends_on: [postgres, redis]

  jira-connector:
    build: ./services/jira-connector
    profiles: [jira]
    depends_on: [postgres, redis]

  confluence-connector:
    build: ./services/confluence-connector
    profiles: [confluence]
    depends_on: [postgres, redis]

  aws-connector:
    build: ./services/aws-connector
    profiles: [aws]
    depends_on: [postgres, redis]

  dashboard-api:
    build: ./services/dashboard-api
    depends_on: [postgres, redis]

  dashboard-ui:
    build: ./services/dashboard-ui
    depends_on: [dashboard-api]

  worker:
    build: ./services/worker
    depends_on: [postgres, redis]
```

**Minimum local footprint** (no optional connectors): `docker compose up` starts core services only. Total RAM: ~600 MB. CPU: 2 cores adequate.

**Full stack:** `docker compose --profile github --profile slack --profile jira --profile confluence --profile aws up`

### 6.2 Kubernetes (v1.1, Optional)

A Helm chart (`charts/apf`) is provided for production Kubernetes deployments. Key design decisions:

- Each service is a `Deployment` with configurable `replicas`.
- `HorizontalPodAutoscaler` configured for `agent-runner` (scale on CPU) and `dashboard-api` (scale on request rate).
- `PersistentVolumeClaim` for PostgreSQL (or external RDS via `externalDatabase.*` values).
- `cert-manager` issues internal TLS certificates.
- `ConfigMap` for non-secret configuration; `ExternalSecrets` operator for secrets (Vault or AWS Secrets Manager).
- `Ingress` (nginx-ingress or AWS ALB) terminates external TLS.
- `NetworkPolicy` restricts inter-service communication to declared ports only.

**Namespace layout:**

```
apf-core:       api-gateway, orchestrator, agent-runner, artifact-store, dashboard-api, dashboard-ui, worker
apf-connectors: github-connector, slack-connector, jira-connector, confluence-connector, aws-connector
apf-infra:      postgres, redis, minio (when not using managed services)
```

### 6.3 GitHub Actions CI/CD

**`.github/workflows/ci.yml`** — triggered on every PR:

```
jobs:
  lint        → eslint/pylint per service
  typecheck   → tsc --noEmit
  unit-test   → jest (Node.js), pytest (Python)
  build       → docker build per service
  integration → docker compose up + API tests (supertest / httpx)
  security    → trivy image scan, semgrep SAST
```

**`.github/workflows/release.yml`** — triggered on tag `v*`:

```
jobs:
  build-push  → docker buildx, push to GHCR with semver tags
  helm-package → helm package charts/apf, push to OCI registry
  sbom        → syft generate SBOM, attach to GitHub release
  release     → gh release create with changelog
```

### 6.4 Environment Strategy

| Environment | Database | Redis | Artifact Store | LLM Provider | Notes |
|---|---|---|---|---|---|
| `development` | SQLite or local PG | Local Redis (Docker) | Local MinIO | Ollama (local) or sandbox API keys | Single `docker compose up` |
| `staging` | PostgreSQL (RDS or local) | Redis (ElastiCache or local) | S3 (separate bucket) | Real API keys, lower-cost models | Mirrors production config; used for integration testing |
| `production` | PostgreSQL (RDS Multi-AZ) | Redis (ElastiCache cluster) | S3 (production bucket) | Real API keys, production models | Full HA, autoscaling, alerts active |

Environment selection is controlled by `APP_ENV` environment variable. Each environment has a corresponding `.env.{environment}` file template (secrets replaced with `<placeholder>`).

---

## 7. Observability

### 7.1 Logging Strategy

All services emit structured JSON logs to stdout. Log format follows the [OTEL log data model](https://opentelemetry.io/docs/specs/otel/logs/data-model/):

```json
{
  "timestamp": "2026-03-23T14:22:01.123Z",
  "severity": "INFO",
  "service": "orchestrator",
  "version": "1.0.0",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "run_id": "01HZ4K8QVTG9M3BZFK5N7WP2XR",
  "stage": "architect",
  "message": "Stage completed successfully",
  "attributes": {
    "duration_ms": 34120,
    "artifact_count": 1,
    "attempt": 1
  }
}
```

**Log levels:** DEBUG (development only), INFO (default), WARN, ERROR, FATAL.

**Correlation IDs:** Every inbound request at the api-gateway receives a `trace_id` (generated if not present in `traceparent` header). The trace_id and run_id propagate through all downstream service calls and log entries.

**Log aggregation:** Logs are consumed by any standard log collector (Fluentd, Vector, AWS CloudWatch Agent). A Grafana Loki configuration example is provided in `docs/observability/loki-config.yaml`.

### 7.2 Metrics

Every service exposes a Prometheus-compatible `/metrics` endpoint on its internal port. Key metrics:

| Metric | Type | Labels | Description |
|---|---|---|---|
| `apf_pipeline_started_total` | Counter | `triggered_by` | Pipelines initiated |
| `apf_pipeline_completed_total` | Counter | `status` | Pipelines completed/failed/cancelled |
| `apf_stage_duration_seconds` | Histogram | `stage`, `status` | Stage execution time |
| `apf_agent_run_duration_seconds` | Histogram | `provider`, `model`, `stage` | LLM call duration |
| `apf_llm_tokens_total` | Counter | `provider`, `model`, `stage`, `type` (input/output) | Token consumption |
| `apf_llm_cost_usd_total` | Counter | `provider`, `model`, `stage` | Cumulative cost |
| `apf_quality_gate_failures_total` | Counter | `stage`, `gate_type` | Quality gate failures |
| `apf_connector_requests_total` | Counter | `connector`, `operation`, `status` | Connector API calls |
| `apf_http_request_duration_seconds` | Histogram | `service`, `method`, `path`, `status` | HTTP request latency |
| `apf_redis_stream_lag` | Gauge | `stream`, `consumer_group` | Consumer group lag |
| `apf_artifact_upload_bytes_total` | Counter | `stage`, `type` | Bytes stored |

**Prometheus scrape config** and **Grafana dashboards** (JSON) are provided under `docs/observability/`.

### 7.3 Distributed Tracing (OpenTelemetry)

Every service initialises an OpenTelemetry SDK tracer at startup. The OTEL exporter is configurable via `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable (defaults to disabled in development).

**Trace structure for a pipeline run:**

```
Trace: pipeline_run (run_id: 01HZ...)
  Span: api-gateway.POST /v1/pipelines
  Span: orchestrator.TriggerPipeline
    Span: orchestrator.execute_stage[prd]
      Span: agent-runner.SubmitAgentJob
        Span: llm.complete (provider=anthropic, model=claude-sonnet-4-5)
      Span: artifact-store.UploadArtifact
    Span: orchestrator.execute_stage[architect]
      ...
    Span: github-connector.CreatePullRequest
```

Trace and span IDs are included in all log entries (see Section 7.1).

### 7.4 Health Check Endpoints

All services implement:

| Endpoint | Type | Returns |
|---|---|---|
| `GET /healthz` | Liveness | `200 OK {"status": "ok"}` always (if process is alive) |
| `GET /readyz` | Readiness | `200 OK {"status": "ready"}` when all dependencies are reachable; `503` otherwise |

The `/readyz` endpoint checks:
- Database connectivity (connection pool ping)
- Redis connectivity (PING command)
- For agent-runner: at least one LLM provider is reachable
- For connectors: connector API endpoint is reachable (if enabled)

**Example Kubernetes liveness/readiness probe configuration:**
```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 10
readinessProbe:
  httpGet:
    path: /readyz
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 15
  failureThreshold: 3
```

---

## 8. Sequence Diagrams

### 8.1 Full Pipeline Execution (Idea → PR)

```
CLI/Browser   api-gateway   orchestrator   agent-runner   artifact-store   github-connector   Redis Streams
    │               │               │               │               │               │               │
    │──POST /v1/pipelines──▶│       │               │               │               │               │
    │               │──gRPC TriggerPipeline──▶│     │               │               │               │
    │               │               │──INSERT pipeline──────────────────────────────────────────────│
    │               │               │──publish pipeline.started──────────────────────────────────▶ │
    │◀──202 Accepted─│               │               │               │               │               │
    │               │               │               │               │               │               │
    │    [Stage: prd]│               │               │               │               │               │
    │               │               │──gRPC SubmitAgentJob──▶│       │               │               │
    │               │               │               │──publish agent_run.started──────────────────▶ │
    │               │               │               │──LLM API call (streaming)      │               │
    │               │               │               │◀──tokens stream────────────────│               │
    │               │               │               │──publish agent_run.token_chunk─────────────▶  │
    │               │               │               │──gRPC UploadArtifact──▶│       │               │
    │               │               │               │               │──write to MinIO│               │
    │               │               │               │               │──INSERT artifact record        │
    │               │               │               │◀──ArtifactMetadata────│       │               │
    │               │               │               │──publish agent_run.completed────────────────▶ │
    │               │               │◀──consume agent_run.completed──────────────────────────────── │
    │               │               │──publish pipeline.stage.completed──────────────────────────▶  │
    │               │               │               │               │               │               │
    │   [Stages: architect, market, ux, engineering, developer, qa, regression, review, devops, readme]
    │               │               │               │               │               │               │
    │    [Final stage completes]     │               │               │               │               │
    │               │               │──gRPC CreateBranch, CommitFiles──────────────▶│               │
    │               │               │               │               │◀──PR created──│               │
    │               │               │               │               │               │──publish github.pr.opened
    │               │               │──publish pipeline.completed──────────────────────────────────▶│
    │               │               │──UPDATE pipeline status        │               │               │
    │  [WebSocket push via Redis pub/sub to dashboard-api clients]   │               │               │
```

### 8.2 Slack HITL Approval Flow

```
orchestrator   Redis Streams   slack-connector   Slack API   User (Slack)   api-gateway
     │               │               │               │               │               │
     │──publish pipeline.gate.pending──────────────▶ │               │               │
     │               │◀──consume gate.pending────────│               │               │
     │               │               │──POST /chat.postMessage (interactive buttons)─▶│
     │               │               │               │──show Approve/Reject buttons──▶│
     │               │               │               │               │               │
     │               │               │               │◀──button click (Approve)───────│
     │               │               │◀──Slack interaction payload──────────────────  │
     │               │               │──POST /v1/webhooks/slack──────────────────────▶│
     │               │               │               │               │   ◀──validate sig─
     │               │               │               │               │──gRPC ApproveGate─▶orchestrator
     │               │               │               │               │               │
     │◀──gate approved────────────────────────────────────────────────────────────────│
     │──resume pipeline execution     │               │               │               │
     │──publish pipeline.gate.approved──────────────▶ │               │               │
     │               │◀──consume gate.approved───────│               │               │
     │               │               │──update Slack message ("Approved by @user")    │
```

### 8.3 AWS Deployment Trigger

```
github-connector   Redis Streams   aws-connector   AWS APIs   slack-connector   dashboard-api
       │               │               │               │               │               │
(PR merged to main webhook received)
       │──publish github.pr.merged──────────────────▶ │               │               │
       │               │◀──consume pr.merged───────────│               │               │
       │               │               │──AssumeRole / resolve creds   │               │
       │               │               │──StartPipelineExecution (CodePipeline) / ECS UpdateService
       │               │               │──publish aws.deployment.triggered──────────────────────▶│
       │               │               │               │               │               │
       │    [Poll deployment status every 15s]         │               │               │
       │               │               │──DescribePipeline / DescribeServices polling──▶│
       │               │               │◀──status response─────────────│               │
       │               │               │──publish aws.deployment.succeeded (or .failed)──────────▶│
       │               │◀──consume deployment.succeeded──────────────────────────────────────────
       │               │               │               │               │               │
       │               │               │──gRPC SendNotification (Slack)─────────────▶ │
       │               │               │               │               │──POST Slack message
       │               │               │               │               │               │
       │               │               │               │               │──WebSocket push to dashboard clients
```

---

## 9. Quality Gates Implementation

### 9.1 Gate Enforcement in the Orchestrator

Quality gates are evaluated by the orchestrator after each stage completes. Gate definitions are declared per stage in the pipeline DAG YAML:

```yaml
# pipeline.yaml
stages:
  - name: prd
    agent: prd
    quality_gates:
      - type: schema_validation
        schema: prd_v1
        blocking: true
      - type: section_completeness
        required_sections: [executive_summary, problem_statement, target_users, goals, core_features]
        blocking: true

  - name: developer
    agent: developer
    quality_gates:
      - type: lint_pass
        blocking: true
      - type: no_hardcoded_secrets
        blocking: true
      - type: build_success
        blocking: true

  - name: qa
    agent: qa
    quality_gates:
      - type: test_pass_rate
        min_pass_rate: 1.0
        blocking: true
      - type: coverage_threshold
        min_coverage: 0.80
        blocking: true

  - name: review
    agent: review
    quality_gates:
      - type: no_critical_sast_findings
        blocking: true
      - type: review_verdict
        allowed: [approve]
        blocking: true
```

**Gate evaluation flow:**

1. Agent-runner completes stage and uploads artifact to artifact-store.
2. Orchestrator calls `artifact-store.ValidateArtifact` (schema validation).
3. Orchestrator evaluates all additional gate types against the artifact content or agent_run metadata.
4. If all blocking gates pass: orchestrator marks stage `completed` and advances the pipeline.
5. If any blocking gate fails: orchestrator marks stage `failed`, increments `attempt`, and either retries (if `attempt < max_attempts`) or halts the pipeline with status `failed`.
6. Gate results are stored in `stages.quality_gate_result` JSONB for audit and dashboard display.

### 9.2 Gate Types

| Gate Type | Evaluated By | Blocking Default |
|---|---|---|
| `schema_validation` | artifact-store (JSON Schema) | Yes |
| `section_completeness` | orchestrator (markdown parser) | Yes |
| `lint_pass` | agent-runner (lint result in artifact metadata) | Yes |
| `build_success` | agent-runner (build result in artifact metadata) | Yes |
| `no_hardcoded_secrets` | agent-runner (secret scanner result) | Yes |
| `test_pass_rate` | agent-runner (test result in artifact metadata) | Yes |
| `coverage_threshold` | agent-runner (coverage report in artifact) | Yes |
| `no_critical_sast_findings` | agent-runner (SAST result in artifact) | Yes |
| `review_verdict` | orchestrator (parsed from `code_review.md` verdict field) | Yes |
| `hitl_approval` | orchestrator (external approval via Slack/dashboard) | Yes |
| `min_competitor_analyses` | orchestrator (count sections in market analysis) | Yes |
| `persona_journey_coverage` | orchestrator (cross-reference PRD personas vs UX journeys) | Yes |

### 9.3 Human-in-the-Loop (HITL) Approval

HITL gates are a special gate type that suspends pipeline execution and waits for explicit human approval. Configuration:

```yaml
stages:
  - name: architect
    agent: architect
    quality_gates:
      - type: hitl_approval
        blocking: true
        timeout_seconds: 86400    # 24 hours
        timeout_action: cancel    # cancel | auto_approve
        approval_channels:
          - slack                 # Send approval request to Slack
          - dashboard             # Show approval button in dashboard
        required_approvers: 1
        approver_roles: [operator, admin]
```

**HITL execution flow:**

1. Stage completes; orchestrator evaluates earlier gates (schema, lint, etc.).
2. Orchestrator publishes `pipeline.gate.pending` event with gate ID, stage, timeout, and channels.
3. Slack connector receives event → sends interactive message with Approve / Reject buttons.
4. Dashboard-api receives event → marks gate as `pending` in UI with countdown timer.
5. Orchestrator sets a Redis key `apf:gate:{gate_id}:timeout` with TTL = `timeout_seconds`.
6. On approval action: api-gateway receives action (Slack webhook or dashboard API call), validates user role, calls `orchestrator.ApprovePipelineGate`.
7. Orchestrator deletes the timeout key, records approver identity in `quality_gate_result`, and advances the pipeline.
8. On timeout: Redis key expiry triggers a worker job that calls `orchestrator.TimeoutGate`; orchestrator applies `timeout_action`.

**Approval audit trail:** Every HITL decision records: approver user_id, timestamp, channel (slack/dashboard), and the gate_id in `stages.quality_gate_result`.

---

## 10. Extension Points

### 10.1 Adding a New Agent

1. **Define the prompt template** in `services/agent-runner/prompts/{new_stage}/v1/` with `system.j2`, `user.j2`, and `schema.json`.

2. **Register the agent** in `services/agent-runner/agents/registry.py`:
   ```python
   from .base import BaseAgent

   class MyCustomAgent(BaseAgent):
       stage_name = "my_stage"
       prompt_template = "my_stage/v1"
       output_schema = "my_stage_output_v1"

   AGENT_REGISTRY["my_stage"] = MyCustomAgent
   ```

3. **Define the artifact schema** in `services/artifact-store/schemas/my_stage_output_v1.json`.

4. **Add the stage to the pipeline DAG** in `pipeline.yaml` with input/output declarations and quality gate configuration.

5. **Write tests** in `services/agent-runner/tests/agents/test_my_stage.py` with mock LLM responses.

No changes to orchestrator, artifact-store, or any other service are required. The orchestrator dispatches agent jobs by stage name, which the agent-runner resolves against the registry.

### 10.2 Adding a New Connector

1. **Create the service** from the connector service template:
   ```bash
   cp -r services/_connector-template services/my-connector
   ```

2. **Implement the gRPC service** defined in `proto/connectors/my_connector.proto`. Register the service in `services/my-connector/src/server.ts`.

3. **Declare event subscriptions** in `services/my-connector/src/events.ts`:
   ```typescript
   export const CONSUMED_STREAMS = [
     { stream: "apf:pipeline", events: ["pipeline.completed"] },
   ];
   ```

4. **Add to Docker Compose** with a profile matching the connector name:
   ```yaml
   my-connector:
     build: ./services/my-connector
     profiles: [my-connector]
     depends_on: [postgres, redis]
   ```

5. **Register the connector config schema** in `services/api-gateway/src/connectors/schemas/my-connector.schema.json`. The api-gateway will automatically expose `PUT /v1/integrations/my-connector` using this schema.

6. **Add the connector to the Helm chart** under `charts/apf/templates/connectors/`.

### 10.3 Plugin API

Plugins hook into pipeline lifecycle events without modifying any service code. Plugins run in the worker service as isolated JavaScript/TypeScript modules.

**Plugin interface:**

```typescript
export interface APFPlugin {
  name: string;
  version: string;

  // Lifecycle hooks (all optional)
  onPipelineStarted?(event: PipelineStartedEvent): Promise<void>;
  onStageCompleted?(event: StageCompletedEvent): Promise<void>;
  onStageFailed?(event: StageFailedEvent): Promise<void>;
  onPipelineCompleted?(event: PipelineCompletedEvent): Promise<void>;
  onPipelineFailed?(event: PipelineFailedEvent): Promise<void>;
  onArtifactUploaded?(event: ArtifactUploadedEvent): Promise<void>;
  onGatePending?(event: GatePendingEvent): Promise<void>;
}
```

**Plugin registration** in `config.yaml`:

```yaml
plugins:
  - path: ./plugins/my-custom-notifier.js
  - package: apf-plugin-pagerduty
  - package: apf-plugin-datadog-events
```

**Plugin execution:** The worker service loads plugins at startup and subscribes them to the relevant Redis Streams. Each plugin's lifecycle hooks are called inside a try/catch; a plugin failure is logged and emitted as a metric (`apf_plugin_error_total`) but does not affect pipeline execution.

**Plugin SDK package:** An npm package `apf-plugin-sdk` is published alongside APF releases. It provides: TypeScript types for all event payloads, a test harness for local plugin development, and utility functions for common operations (fetch artifact content, post Slack messages via the API).

---

*End of Architecture Document*

*This document is the authoritative reference for all engineering decisions in APF v1.0. All significant deviations must be captured as new ADRs appended to Section 1.2 and reviewed by the Engineering Lead before implementation.*
