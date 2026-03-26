# Autonomous Product Factory — UX Specification

**Document version:** 1.0
**Date:** 2026-03-23
**Status:** Draft

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [CLI Interface](#2-cli-interface)
3. [Web Dashboard](#3-web-dashboard)
4. [Slack Bot UX](#4-slack-bot-ux)
5. [Jira Bot UX](#5-jira-bot-ux)
6. [Confluence Bot UX](#6-confluence-bot-ux)
7. [AWS Bot UX](#7-aws-bot-ux)
8. [User Flows](#8-user-flows)
9. [Error States and Recovery Paths](#9-error-states-and-recovery-paths)
10. [Accessibility Notes](#10-accessibility-notes)

---

## 1. Design Principles

These principles govern every interface in the APF system — CLI, web dashboard, and external integrations.

### 1.1 Transparency First
Every agent action must be observable. Users should never wonder what the pipeline is doing. Progress, decisions, and failures are surfaced proactively and in plain language.

### 1.2 Progressive Disclosure
Simple outputs by default; verbose detail on demand. The CLI defaults to summary output; `--verbose` expands it. The dashboard shows stage cards at a glance; clicking opens full logs and artifacts.

### 1.3 Minimal Interruption
The pipeline runs autonomously. Human intervention is only requested at explicitly gated stages or on unrecoverable errors. Approval prompts are clear, actionable, and time-bounded.

### 1.4 Recoverable by Design
Every error message includes a recovery path — what went wrong, why, and what the user should do next. No dead ends.

### 1.5 Consistent Vocabulary
Stage names, status labels, and action verbs are identical across CLI, dashboard, Slack, Jira, and Confluence. The canonical stage names are:

| Stage ID         | Display Name          |
|------------------|-----------------------|
| `intake`         | Idea Intake           |
| `prd`            | PRD Generation        |
| `architecture`   | Architecture Design   |
| `ux`             | UX Specification      |
| `planning`       | Sprint Planning       |
| `coding`         | Code Generation       |
| `review`         | Code Review           |
| `testing`        | Automated Testing     |
| `deployment`     | Deployment            |

### 1.6 Status Vocabulary
Status labels are consistent everywhere:

| Status       | Meaning                                         |
|--------------|-------------------------------------------------|
| `pending`    | Not yet started                                 |
| `running`    | Agent actively working                          |
| `awaiting`   | Blocked, waiting for human approval             |
| `complete`   | Finished successfully                           |
| `failed`     | Terminated with an error                        |
| `skipped`    | Bypassed by user or configuration               |

---

## 2. CLI Interface

### 2.1 Global Conventions

**Binary name:** `apf`

**Exit codes:**

| Code | Meaning                        |
|------|--------------------------------|
| `0`  | Success                        |
| `1`  | General error                  |
| `2`  | Invalid arguments / flags      |
| `3`  | Pipeline stage failed          |
| `4`  | Awaiting approval (non-fatal)  |
| `5`  | Connector / integration error  |

**Global flags available on every command:**

| Flag              | Short | Default    | Description                              |
|-------------------|-------|------------|------------------------------------------|
| `--project <id>`  | `-p`  | `.apf.yml` | Target project ID or config path         |
| `--output <fmt>`  | `-o`  | `pretty`   | Output format: `pretty`, `json`, `plain` |
| `--verbose`       | `-v`  | `false`    | Show full detail instead of summaries    |
| `--no-color`      |       | `false`    | Disable ANSI color codes                 |
| `--quiet`         | `-q`  | `false`    | Suppress all output except errors        |
| `--help`          | `-h`  |            | Show help for the command                |

**Output format behavior:**
- `pretty` — colored, human-readable tables and spinners. Used by default in TTY environments.
- `json` — machine-readable JSON on stdout. Suitable for scripting and CI pipelines.
- `plain` — uncolored text with consistent delimiters. Suitable for log capture.

---

### 2.2 `apf init`

Initialize a new APF project in the current directory or a specified path.

**Syntax:**
```
apf init [<directory>] [flags]
```

**Arguments:**

| Argument      | Required | Description                          |
|---------------|----------|--------------------------------------|
| `<directory>` | No       | Target directory. Defaults to `.`    |

**Flags:**

| Flag                   | Default    | Description                                               |
|------------------------|------------|-----------------------------------------------------------|
| `--name <name>`        |            | Project name. Prompted interactively if omitted.          |
| `--template <id>`      | `default`  | Starter template: `default`, `api`, `fullstack`, `cli`    |
| `--connectors <list>`  | `none`     | Comma-separated connectors to enable: `slack,jira,confluence,aws` |
| `--non-interactive`    | `false`    | Skip all prompts; fail if required values are missing     |
| `--force`              | `false`    | Overwrite existing `.apf.yml` if present                  |

**Interactive prompts (when `--non-interactive` is not set):**

```
? Project name: my-saas-product
? Select a template:
  > default
    api
    fullstack
    cli
? Enable connectors (space to select, enter to confirm):
  > [ ] Slack
    [ ] Jira
    [ ] Confluence
    [ ] AWS
? Approve gated stages manually? (Y/n): Y
```

**Success output (`pretty`):**
```
✓ Initialized APF project "my-saas-product"

  Config:   ./my-saas-product/.apf.yml
  Template: default
  Stages:   intake → prd → architecture → ux → planning → coding → review → testing → deployment

  Next steps:
    apf run "<your idea>"        Run the full pipeline
    apf connectors               Configure integrations
```

**Success output (`json`):**
```json
{
  "status": "ok",
  "project": "my-saas-product",
  "config_path": "./my-saas-product/.apf.yml",
  "template": "default",
  "connectors_enabled": []
}
```

**Error messages:**

| Condition                       | Message                                                                      |
|---------------------------------|------------------------------------------------------------------------------|
| Directory already has `.apf.yml`| `Error: .apf.yml already exists. Use --force to overwrite.`                 |
| Invalid template ID             | `Error: Unknown template "xyz". Run 'apf init --help' to see valid values.` |
| Directory not writable          | `Error: Cannot write to "<path>". Check permissions.`                        |

---

### 2.3 `apf run`

Start the full pipeline from the beginning, or resume from a specific stage.

**Syntax:**
```
apf run "<idea>" [flags]
apf run [flags]       # resumes if a pipeline is already initialized
```

**Arguments:**

| Argument  | Required | Description                                    |
|-----------|----------|------------------------------------------------|
| `<idea>`  | Conditional | The raw product idea as a quoted string. Required when starting a new run; optional when resuming. |

**Flags:**

| Flag                     | Default | Description                                                           |
|--------------------------|---------|-----------------------------------------------------------------------|
| `--from <stage>`         |         | Resume pipeline from this stage ID (skips earlier stages)             |
| `--to <stage>`           |         | Stop pipeline after this stage ID (does not run later stages)         |
| `--skip <stage>`         |         | Comma-separated stage IDs to skip entirely                            |
| `--auto-approve`         | `false` | Automatically approve all gated stages without human input            |
| `--approve-timeout <d>`  | `24h`   | Duration to wait for manual approval before auto-failing              |
| `--dry-run`              | `false` | Validate configuration and show planned execution; do not run agents  |
| `--watch`                | `false` | Tail live output after starting (equivalent to `apf logs --follow`)   |

**Behavior:**
- Without `--from`, a new pipeline run is created with a unique run ID.
- With `--from <stage>`, the most recent run is resumed from that stage, preserving all previous artifacts.
- `--from` and `--to` can be combined to run a sub-range of stages.

**Output on start (`pretty`):**
```
▶ Starting pipeline run [run-id: a1b2c3d4]

  Idea: "A SaaS tool that lets small teams manage customer feedback"
  Stages: intake → prd → architecture → ux → planning → coding → review → testing → deployment

  Tracking: apf status --run=a1b2c3d4
  Logs:     apf logs --run=a1b2c3d4 --follow

  [12:01:05] intake       running  Extracting requirements from idea…
```

**With `--watch`, output streams continuously:**
```
  [12:01:05] intake       running  Extracting requirements from idea…
  [12:01:18] intake       complete Extracted 12 requirements, 3 constraints
  [12:01:18] prd          running  Drafting Product Requirements Document…
  [12:03:44] prd          complete PRD written (2,847 words)
  [12:03:44] architecture running  Designing system architecture…
  …
```

**Dry-run output:**
```
Dry run — no agents will be started.

  Pipeline plan for run "<idea>":
  ┌─────────────┬────────────┐
  │ Stage       │ Action     │
  ├─────────────┼────────────┤
  │ intake      │ run        │
  │ prd         │ run        │
  │ architecture│ run        │
  │ ux          │ SKIP       │
  │ planning    │ run        │
  │ coding      │ run        │
  │ review      │ GATE (manual approval required) │
  │ testing     │ run        │
  │ deployment  │ GATE (manual approval required) │
  └─────────────┴────────────┘
```

**Error messages:**

| Condition                   | Message                                                                               |
|-----------------------------|---------------------------------------------------------------------------------------|
| No `.apf.yml` found         | `Error: No APF project found. Run 'apf init' first.`                                 |
| Invalid `--from` stage      | `Error: Unknown stage "xyz". Valid stages: intake, prd, architecture, ux, planning, coding, review, testing, deployment` |
| Pipeline already running    | `Error: A pipeline run (a1b2c3d4) is already active. Use 'apf status' to check progress or 'apf run --from=<stage>' to restart from a specific stage.` |
| Idea too short              | `Error: Idea must be at least 10 characters.`                                        |

---

### 2.4 `apf status`

Show the current state of the pipeline and each stage.

**Syntax:**
```
apf status [flags]
```

**Flags:**

| Flag              | Description                                    |
|-------------------|------------------------------------------------|
| `--run <id>`      | Show status for a specific run ID              |
| `--watch`         | Refresh every 3 seconds until pipeline ends    |
| `--stage <id>`    | Show status for one specific stage only        |

**Output (`pretty`):**
```
Pipeline: my-saas-product  [run: a1b2c3d4]  started 12:01:05  elapsed 00:14:32

  ✓  intake         complete   00:00:13
  ✓  prd            complete   00:02:26
  ✓  architecture   complete   00:05:17
  ✓  ux             complete   00:03:10
  ●  planning       running    00:03:26  Generating sprint backlog…
  ○  coding         pending    —
  ○  review         pending    —
  ○  testing        pending    —
  ○  deployment     pending    —

  Use 'apf logs planning' to stream the current stage output.
```

**Legend:**
```
✓ complete   ● running   ⚑ awaiting   ✗ failed   ○ pending   — skipped
```

**Output (`json`):**
```json
{
  "run_id": "a1b2c3d4",
  "project": "my-saas-product",
  "started_at": "2026-03-23T12:01:05Z",
  "elapsed_seconds": 872,
  "overall_status": "running",
  "stages": [
    { "id": "intake",       "status": "complete", "duration_seconds": 13  },
    { "id": "prd",          "status": "complete", "duration_seconds": 146 },
    { "id": "architecture", "status": "complete", "duration_seconds": 317 },
    { "id": "ux",           "status": "complete", "duration_seconds": 190 },
    { "id": "planning",     "status": "running",  "duration_seconds": 206 },
    { "id": "coding",       "status": "pending",  "duration_seconds": null },
    { "id": "review",       "status": "pending",  "duration_seconds": null },
    { "id": "testing",      "status": "pending",  "duration_seconds": null },
    { "id": "deployment",   "status": "pending",  "duration_seconds": null }
  ]
}
```

---

### 2.5 `apf logs`

Stream or display logs for a specific stage.

**Syntax:**
```
apf logs <stage> [flags]
```

**Arguments:**

| Argument  | Required | Description              |
|-----------|----------|--------------------------|
| `<stage>` | Yes      | Stage ID to show logs for |

**Flags:**

| Flag           | Default | Description                                      |
|----------------|---------|--------------------------------------------------|
| `--run <id>`   |         | Target a specific run ID                         |
| `--follow`     | `false` | Stream logs in real time (exit with Ctrl+C)      |
| `--tail <n>`   | `50`    | Number of lines to show from the end             |
| `--since <ts>` |         | Show logs since a timestamp (ISO 8601 or offset like `5m`) |
| `--level <l>`  | `info`  | Minimum log level: `debug`, `info`, `warn`, `error` |

**Output:**
```
[12:05:44 INFO ] planning  Parsing PRD artifacts…
[12:05:45 INFO ] planning  Identified 7 epics, 24 user stories
[12:05:46 INFO ] planning  Assigning story points using T-shirt sizing…
[12:05:50 WARN ] planning  Story AP-019 has no clear acceptance criteria; using best guess
[12:05:51 INFO ] planning  Sprint plan generated: 3 sprints, 24 stories
```

**Error messages:**

| Condition              | Message                                                              |
|------------------------|----------------------------------------------------------------------|
| Stage not found        | `Error: Unknown stage "xyz". Run 'apf status' to see valid stages.` |
| No logs yet            | `No logs available for stage "intake" in run a1b2c3d4 yet.`        |
| Stage not started      | `Stage "coding" has not started. Current stage is "planning".`      |

---

### 2.6 `apf approve`

Manually approve or reject a gated stage that is awaiting human review.

**Syntax:**
```
apf approve <stage> [flags]
```

**Arguments:**

| Argument  | Required | Description                   |
|-----------|----------|-------------------------------|
| `<stage>` | Yes      | Stage ID to approve or reject |

**Flags:**

| Flag              | Default  | Description                                    |
|-------------------|----------|------------------------------------------------|
| `--run <id>`      |          | Target a specific run ID                       |
| `--reject`        | `false`  | Reject instead of approve                      |
| `--message <msg>` |          | Optional comment attached to the decision      |
| `--yes`           | `false`  | Skip interactive confirmation prompt           |

**Interactive confirmation (when `--yes` is not set):**
```
Stage "review" is awaiting your approval.

  Summary: Code Review complete. 3 issues flagged (2 minor, 1 moderate).
  Artifact: .apf/artifacts/review/report.md

? Approve this stage and continue the pipeline? (y/N): y
```

**Success output:**
```
✓ Stage "review" approved by <user> at 14:33:02

  Pipeline will now proceed to "testing".
```

**Rejection output:**
```
✗ Stage "review" rejected by <user> at 14:33:02

  Message: "The moderate issue in auth.ts must be resolved first."

  Pipeline is paused. To re-run from this stage after fixing:
    apf run --from=review
```

**Error messages:**

| Condition                   | Message                                                                      |
|-----------------------------|------------------------------------------------------------------------------|
| Stage not awaiting approval | `Error: Stage "review" is not awaiting approval (current status: running).` |
| No active run               | `Error: No active pipeline run found. Use --run=<id> to specify one.`       |

---

### 2.7 `apf connectors`

List, enable, disable, and configure external integrations.

**Syntax:**
```
apf connectors [subcommand] [flags]
```

**Subcommands:**

| Subcommand             | Description                                      |
|------------------------|--------------------------------------------------|
| `list`                 | Show all connectors and their status (default)   |
| `enable <connector>`   | Enable a connector and start its setup wizard    |
| `disable <connector>`  | Disable a connector                              |
| `configure <connector>`| Re-run setup wizard for an already-enabled connector |
| `test <connector>`     | Send a test event to verify configuration        |

**Valid connector IDs:** `slack`, `jira`, `confluence`, `aws`

**`apf connectors list` output:**
```
Connectors for project "my-saas-product":

  NAME          STATUS    DETAILS
  ──────────────────────────────────────────────────────
  slack         enabled   Workspace: Acme Corp  Channel: #apf-notifications
  jira          enabled   Project: SAAS  Board: APF Sprint Board
  confluence    disabled  —
  aws           disabled  —

  Use 'apf connectors enable <name>' to configure.
```

**`apf connectors enable slack` interactive wizard:**
```
Enabling Slack connector.

? Slack Bot Token (xoxb-…): ••••••••••••••••••••
? Default notification channel: #apf-notifications
? Notify on stage complete? (Y/n): Y
? Notify on errors? (Y/n): Y
? Notify on approval requests? (Y/n): Y

Testing connection… ✓ Connected to workspace "Acme Corp"
Sending test message to #apf-notifications… ✓ Message delivered

✓ Slack connector enabled.
```

**`apf connectors enable jira` interactive wizard:**
```
Enabling Jira connector.

? Jira base URL: https://acme.atlassian.net
? Jira email: dev@acme.com
? Jira API token: ••••••••••••••••••••
? Jira project key: SAAS
? Default issue type: Story

Testing connection… ✓ Connected to Jira project "SAAS"

✓ Jira connector enabled.
```

**`apf connectors enable confluence` interactive wizard:**
```
Enabling Confluence connector.

? Confluence base URL: https://acme.atlassian.net/wiki
? Confluence email: dev@acme.com
? Confluence API token: ••••••••••••••••••••
? Target space key: ENG
? Parent page title (leave blank for space root): APF Artifacts

Testing connection… ✓ Connected to space "ENG"

✓ Confluence connector enabled.
```

**`apf connectors enable aws` interactive wizard:**
```
Enabling AWS connector.

? AWS region: us-east-1
? Authentication method:
  > IAM Role (recommended)
    Access Key + Secret
? IAM Role ARN: arn:aws:iam::123456789012:role/apf-deploy-role
? Deployment target:
  > ECS
    Lambda
    Elastic Beanstalk
    S3 (static site)
? ECS cluster name: my-app-cluster
? ECS service name: my-app-service

Testing connection… ✓ AssumeRole successful. ECS cluster reachable.

✓ AWS connector enabled.
```

**Error messages:**

| Condition               | Message                                                                  |
|-------------------------|--------------------------------------------------------------------------|
| Invalid connector name  | `Error: Unknown connector "github". Valid connectors: slack, jira, confluence, aws` |
| Auth test failed        | `Error: Could not connect to Slack. Check your bot token and try again.` |
| Already enabled         | `Connector "slack" is already enabled. Use 'apf connectors configure slack' to update settings.` |

---

## 3. Web Dashboard

### 3.1 Design Principles (Dashboard-Specific)

- **Density with clarity:** Display maximum useful information per screen without visual clutter. Use whitespace strategically.
- **Warm neutrals + semantic color:** Background in off-white/dark-mode dark-gray. Use color only for status (green = complete, amber = running/awaiting, red = failed, gray = pending).
- **Real-time by default:** All stage cards and log streams auto-update via WebSocket. No manual refresh required.
- **Action proximity:** Approval buttons, log links, and artifact links are placed adjacent to the data they act on, not in a separate panel.

---

### 3.2 Component Inventory

| Component ID             | Type           | Description                                                  |
|--------------------------|----------------|--------------------------------------------------------------|
| `StageCard`              | Card           | Shows stage name, status badge, duration, and action links   |
| `StatusBadge`            | Badge          | Color-coded label for pipeline status values                  |
| `ProgressRing`           | Indicator      | Circular progress indicator for running stages               |
| `LogStream`              | Panel          | Auto-scrolling log viewer with level filtering               |
| `ArtifactViewer`         | Panel          | Renders markdown artifacts (PRD, architecture, etc.)         |
| `ApprovalPanel`          | Modal/Panel    | Displays approval context and Approve/Reject action buttons  |
| `ConnectorCard`          | Card           | Shows connector name, status, and configure button           |
| `ConnectorWizard`        | Modal          | Multi-step form for connector setup                          |
| `PipelineTimeline`       | Timeline       | Horizontal timeline of all stages with status icons          |
| `RunSelector`            | Dropdown       | Switch between historical pipeline runs                      |
| `SearchBar`              | Input          | Filter logs or artifact content                              |
| `ToastNotification`      | Toast          | Ephemeral non-blocking alerts (success, warning, error)      |
| `EmptyState`             | Placeholder    | Illustrated empty state with a primary call-to-action        |
| `SideNav`                | Navigation     | Collapsible left navigation with page links                  |
| `TopBar`                 | Navigation     | Project selector, run selector, and user menu                |

---

### 3.3 Screen: Pipeline Overview

**Route:** `/`

**Purpose:** Central hub showing the status of all stages in the active run at a glance.

**Wireframe description:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ TOP BAR                                                              │
│  [APF Logo]  [Project: my-saas-product ▼]  [Run: a1b2c3d4 ▼]  [👤] │
├────────┬─────────────────────────────────────────────────────────────┤
│ SIDE   │ MAIN CONTENT                                                │
│ NAV    │                                                             │
│        │  Pipeline Overview                       Elapsed: 00:14:32  │
│ ● Over-│                                                             │
│   view │  PIPELINE TIMELINE                                          │
│        │  intake──►prd──►architecture──►ux──►planning──►…           │
│ ○ Arti-│  ✓        ✓     ✓             ✓    ●          ○ ○ ○ ○     │
│   facts│                                                             │
│        │  STAGE CARDS (grid, 3 per row)                              │
│ ○ Logs │                                                             │
│        │  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐  │
│ ○ Conn-│  │ ✓ Idea Intake  │ │ ✓ PRD          │ │ ✓ Architecture │  │
│   ecto-│  │ complete       │ │ complete       │ │ complete       │  │
│   rs   │  │ 00:00:13       │ │ 00:02:26       │ │ 00:05:17       │  │
│        │  │ [View Artifact]│ │ [View Artifact]│ │ [View Artifact]│  │
│ ○ Sett-│  │ [View Logs]    │ │ [View Logs]    │ │ [View Logs]    │  │
│   ings │  └────────────────┘ └────────────────┘ └────────────────┘  │
│        │                                                             │
│        │  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐  │
│        │  │ ✓ UX Spec      │ │ ● Sprint Plan  │ │ ○ Code Gen     │  │
│        │  │ complete       │ │ running        │ │ pending        │  │
│        │  │ 00:03:10       │ │ 00:03:26 ◌     │ │ —              │  │
│        │  │ [View Artifact]│ │ Generating...  │ │                │  │
│        │  │ [View Logs]    │ │ [View Logs]    │ │                │  │
│        │  └────────────────┘ └────────────────┘ └────────────────┘  │
│        │                                                             │
│        │  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐  │
│        │  │ ○ Code Review  │ │ ○ Testing      │ │ ○ Deployment   │  │
│        │  │ pending        │ │ pending        │ │ pending        │  │
│        │  └────────────────┘ └────────────────┘ └────────────────┘  │
│        │                                                             │
└────────┴─────────────────────────────────────────────────────────────┘
```

**Stage Card states:**

- **Pending:** Gray border, stage name, "pending" label, no action links.
- **Running:** Amber border, `ProgressRing` spinner, elapsed timer ticking, "View Logs" link.
- **Awaiting:** Amber border with pulsing indicator, "AWAITING APPROVAL" badge, "Review & Approve" button (opens `ApprovalPanel`).
- **Complete:** Green border, elapsed time, "View Artifact" and "View Logs" links.
- **Failed:** Red border, error summary (first line of error), "View Logs" and "Retry" links.
- **Skipped:** Gray border, dashed outline, "skipped" label.

**Interactions:**
- Clicking a stage card expands it inline to show the last 20 log lines.
- Clicking "View Artifact" navigates to the Artifact Viewer for that stage.
- Clicking "View Logs" navigates to the Logs page pre-filtered to that stage.
- The `PipelineTimeline` is sticky at the top of the main content area during scroll.

---

### 3.4 Screen: Artifact Viewer

**Route:** `/artifacts/<stage>`

**Purpose:** Display the rendered markdown artifact produced by a stage (PRD, architecture doc, UX spec, sprint plan, code review report).

**Wireframe description:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ TOP BAR                                                              │
├────────┬─────────────────────────────────────────────────────────────┤
│ SIDE   │ ARTIFACT VIEWER                                             │
│ NAV    │                                                             │
│        │  ← Back to Overview                                         │
│        │                                                             │
│        │  Stage: PRD Generation        [Download .md]  [Copy link]  │
│        │  Run: a1b2c3d4  │  Completed: 12:03:44                     │
│        │                                                             │
│        │  ┌─────────────────────────────────────────────────────┐   │
│        │  │                                                     │   │
│        │  │  # Product Requirements Document                    │   │
│        │  │                                                     │   │
│        │  │  ## Overview                                        │   │
│        │  │  This document defines requirements for…            │   │
│        │  │                                                     │   │
│        │  │  ## User Stories                                    │   │
│        │  │  1. As a team lead, I want to…                      │   │
│        │  │                                                     │   │
│        │  │  [Rendered markdown content continues…]             │   │
│        │  │                                                     │   │
│        │  └─────────────────────────────────────────────────────┘   │
│        │                                                             │
│        │  ARTIFACT NAVIGATION                                        │
│        │  ← Architecture Design (prev)    UX Specification (next) → │
└────────┴─────────────────────────────────────────────────────────────┘
```

**Behaviors:**
- Markdown is rendered with syntax highlighting for code blocks.
- A floating table of contents is shown on the right for long documents.
- "Download .md" downloads the raw markdown file.
- If the artifact is not yet available (stage pending/running), the viewer shows an `EmptyState` with a spinner and "Waiting for stage to complete…".

---

### 3.5 Screen: Live Agent Log Stream

**Route:** `/logs`

**Purpose:** View and filter real-time log output from any stage.

**Wireframe description:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ TOP BAR                                                              │
├────────┬─────────────────────────────────────────────────────────────┤
│ SIDE   │ LOGS                                                        │
│ NAV    │                                                             │
│        │  FILTERS                                                    │
│        │  Stage: [planning ▼]  Level: [INFO ▼]  [🔍 Search logs…]   │
│        │  [● Live]  [Pause]                                          │
│        │                                                             │
│        │  ┌─────────────────────────────────────────────────────┐   │
│        │  │ [12:05:44 INFO ] Parsing PRD artifacts…             │   │
│        │  │ [12:05:45 INFO ] Identified 7 epics, 24 stories     │   │
│        │  │ [12:05:46 INFO ] Assigning story points…            │   │
│        │  │ [12:05:50 WARN ] Story AP-019 has no clear ACs      │   │
│        │  │ [12:05:51 INFO ] Sprint plan generated              │   │
│        │  │                                            ▌ cursor │   │
│        │  └─────────────────────────────────────────────────────┘   │
│        │                                                             │
│        │  [Jump to bottom ↓]                                         │
└────────┴─────────────────────────────────────────────────────────────┘
```

**Behaviors:**
- Log lines are color-coded by level: DEBUG = gray, INFO = default, WARN = amber, ERROR = red.
- "Pause" freezes the auto-scroll so the user can read without the view jumping.
- "Live" indicator pulses green when connected via WebSocket; shows a disconnected amber warning if the stream drops, with an auto-reconnect attempt.
- Search highlights matching terms inline without filtering out non-matching lines.
- Clicking a log line expands it to show full structured log data (JSON metadata if available).

---

### 3.6 Screen: Approval / Intervention Panel

**Route:** `/approve/<stage>` (also accessible as an overlay from the Pipeline Overview)

**Purpose:** Present a gated stage to the user for approval or rejection with full context.

**Wireframe description:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ TOP BAR                                                              │
├────────┬─────────────────────────────────────────────────────────────┤
│ SIDE   │ APPROVAL REQUIRED                                           │
│ NAV    │                                                             │
│        │  ⚑ Stage "Code Review" is awaiting your approval.          │
│        │    Pipeline is paused.  Timeout in: 23h 41m                │
│        │                                                             │
│        │  SUMMARY                                                    │
│        │  ┌─────────────────────────────────────────────────────┐   │
│        │  │ Code review complete.                               │   │
│        │  │                                                     │   │
│        │  │ Issues found: 3                                     │   │
│        │  │   • 2 minor — style and naming conventions          │   │
│        │  │   • 1 moderate — potential null dereference in      │   │
│        │  │     auth/session.ts line 84                         │   │
│        │  │                                                     │   │
│        │  │ [View Full Review Report →]                         │   │
│        │  └─────────────────────────────────────────────────────┘   │
│        │                                                             │
│        │  COMMENT (optional)                                         │
│        │  ┌─────────────────────────────────────────────────────┐   │
│        │  │ Add a note about your decision…                     │   │
│        │  └─────────────────────────────────────────────────────┘   │
│        │                                                             │
│        │  [✓ Approve — continue to Testing]  [✗ Reject — pause]    │
│        │                                                             │
│        │  Approved by will be recorded in the audit log.            │
└────────┴─────────────────────────────────────────────────────────────┘
```

**Behaviors:**
- If the approval timeout expires before an action is taken, the stage auto-fails and a `ToastNotification` is shown with a "Re-run from this stage" link.
- Approving updates the stage status to `running` (pipeline resumes) immediately with an optimistic UI update, confirmed by WebSocket event.
- Rejecting updates stage to `failed` and shows next-step guidance.
- All approval decisions are written to an audit log with timestamp and user identity.

---

### 3.7 Screen: Connector Configuration UI

**Route:** `/connectors`

**Purpose:** Manage all external integrations from a single screen.

**Wireframe description:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ TOP BAR                                                              │
├────────┬─────────────────────────────────────────────────────────────┤
│ SIDE   │ CONNECTORS                                                  │
│ NAV    │                                                             │
│        │  ┌──────────────────────────────────────────────────────┐  │
│        │  │  🟢  Slack                              [Configure]  │  │
│        │  │       Workspace: Acme Corp                           │  │
│        │  │       Channel: #apf-notifications                    │  │
│        │  │       Last event: 2 min ago         [Test]  [Disable]│  │
│        │  └──────────────────────────────────────────────────────┘  │
│        │                                                             │
│        │  ┌──────────────────────────────────────────────────────┐  │
│        │  │  🟢  Jira                               [Configure]  │  │
│        │  │       Project: SAAS                                  │  │
│        │  │       Last ticket: SAAS-42              [Test]  [Disable]│
│        │  └──────────────────────────────────────────────────────┘  │
│        │                                                             │
│        │  ┌──────────────────────────────────────────────────────┐  │
│        │  │  ⚫  Confluence                         [Enable →]   │  │
│        │  │       Not configured                                 │  │
│        │  └──────────────────────────────────────────────────────┘  │
│        │                                                             │
│        │  ┌──────────────────────────────────────────────────────┐  │
│        │  │  ⚫  AWS                                [Enable →]   │  │
│        │  │       Not configured                                 │  │
│        │  └──────────────────────────────────────────────────────┘  │
└────────┴─────────────────────────────────────────────────────────────┘
```

**`ConnectorWizard` modal (multi-step):**
- Step 1: Credentials (API token, URL, etc.)
- Step 2: Configuration (channels, projects, targets)
- Step 3: Notification preferences
- Step 4: Test connection (live feedback with pass/fail)
- Step 5: Confirmation summary

**Behaviors:**
- "Test" sends a real test event and shows inline pass/fail feedback without leaving the page.
- "Disable" shows a confirmation modal before disabling to prevent accidental disconnection.
- Credentials are masked after initial entry and shown only as placeholder dots. A "Re-enter credentials" button clears and re-prompts.

---

## 4. Slack Bot UX

### 4.1 Command Reference

All APF commands are invoked with the `/apf` slash command prefix in any Slack channel or DM where the bot is present.

| Command                          | Description                                    |
|----------------------------------|------------------------------------------------|
| `/apf run "<idea>"`              | Start a new pipeline run                       |
| `/apf run --from=<stage>`        | Resume an existing run from a stage            |
| `/apf status`                    | Show current pipeline status                   |
| `/apf status --run=<id>`         | Show status for a specific run                 |
| `/apf approve <stage>`           | Approve a gated stage                          |
| `/apf approve <stage> --reject`  | Reject a gated stage                           |
| `/apf logs <stage>`              | Post the last 20 log lines to Slack            |
| `/apf help`                      | Show command reference                         |

---

### 4.2 Notification Message Formats

All APF Slack messages use Block Kit layout. Fields are described in plain text here.

**Stage Started:**
```
┌─────────────────────────────────────────────────────┐
│ 🔄  APF Pipeline — Stage Started                    │
│                                                     │
│  Project:  my-saas-product                         │
│  Stage:    Sprint Planning                          │
│  Run ID:   a1b2c3d4                                 │
│  Started:  12:05:44                                 │
│                                                     │
│  [View Live Logs ↗]                                 │
└─────────────────────────────────────────────────────┘
```

**Stage Complete:**
```
┌─────────────────────────────────────────────────────┐
│ ✅  APF Pipeline — Stage Complete                   │
│                                                     │
│  Project:   my-saas-product                        │
│  Stage:     PRD Generation                          │
│  Run ID:    a1b2c3d4                                │
│  Duration:  2m 26s                                  │
│  Artifact:  PRD (2,847 words)                       │
│                                                     │
│  [View Artifact ↗]  [View Logs ↗]                   │
└─────────────────────────────────────────────────────┘
```

**Awaiting Approval:**
```
┌─────────────────────────────────────────────────────┐
│ ⚑  APF Pipeline — Approval Required                │
│                                                     │
│  Project:  my-saas-product                         │
│  Stage:    Code Review                              │
│  Run ID:   a1b2c3d4                                 │
│                                                     │
│  Summary:                                           │
│  Code review complete. 3 issues found (2 minor,    │
│  1 moderate). Review the report before approving.  │
│                                                     │
│  Timeout:  23h 41m remaining                        │
│                                                     │
│  [View Report ↗]                                    │
│                                                     │
│  [ ✓ Approve ]          [ ✗ Reject ]               │
└─────────────────────────────────────────────────────┘
```

**Error / Stage Failed:**
```
┌─────────────────────────────────────────────────────┐
│ ❌  APF Pipeline — Stage Failed                     │
│                                                     │
│  Project:  my-saas-product                         │
│  Stage:    Code Generation                          │
│  Run ID:   a1b2c3d4                                 │
│  Error:    LLM API timeout after 3 retries         │
│                                                     │
│  [View Logs ↗]  [Retry Stage ↗]                     │
└─────────────────────────────────────────────────────┘
```

**Pipeline Complete:**
```
┌─────────────────────────────────────────────────────┐
│ 🎉  APF Pipeline — Complete                         │
│                                                     │
│  Project:   my-saas-product                        │
│  Run ID:    a1b2c3d4                                │
│  Total:     1h 12m 33s                              │
│  PR:        github.com/acme/my-saas-product/pull/7  │
│                                                     │
│  [View Dashboard ↗]  [View PR ↗]                    │
└─────────────────────────────────────────────────────┘
```

---

### 4.3 Interactive Button Behavior

**Approve button:**
- On click: Button is replaced with a spinner "Processing…" for 1–2 seconds.
- On success: Message updates to show "✅ Approved by @username at HH:MM" with buttons removed.
- On failure (stage no longer awaiting): Message updates to "This approval request is no longer active."

**Reject button:**
- On click: A modal dialog opens with a text field: "Reason for rejection (optional):" and a "Confirm Rejection" button.
- On confirm: Message updates to show "✗ Rejected by @username at HH:MM — Reason: <text>".

**Ephemeral responses to slash commands:**
- `/apf status` — response is visible only to the invoking user (ephemeral) to avoid channel noise.
- `/apf logs <stage>` — response is ephemeral, contains last 20 lines as a code block.
- `/apf approve <stage>` — confirmation is posted visibly in the channel so the team can see the decision.

---

### 4.4 Bot Permission Scopes Required

| Scope               | Purpose                                      |
|---------------------|----------------------------------------------|
| `commands`          | Register `/apf` slash command                |
| `chat:write`        | Post messages and notifications              |
| `chat:write.public` | Post in channels without being a member      |
| `users:read`        | Resolve user identity for approval audit log |

---

## 5. Jira Bot UX

### 5.1 Auto-Ticket Creation

A Jira issue is automatically created when each stage begins and updated when it completes.

**Ticket creation trigger:** Stage status transitions to `running`.
**Ticket update trigger:** Stage status transitions to `complete`, `failed`, or `awaiting`.

### 5.2 Ticket Field Mapping

| Jira Field       | Value                                                       |
|------------------|-------------------------------------------------------------|
| **Summary**      | `[APF] <Display Name> — <Project Name> (run: <run_id>)`    |
| **Description**  | Stage description + artifact link (if available) + log URL  |
| **Issue Type**   | `Story` (configurable per connector setup)                  |
| **Priority**     | `Medium` by default; `High` if stage is gated               |
| **Labels**       | `apf`, `apf-<stage_id>`, `apf-run-<run_id>`                |
| **Reporter**     | APF bot service account                                     |
| **Assignee**     | Unassigned (configurable to assign to a default user)       |
| **Epic Link**    | Links to a parent epic `[APF] <Project Name>` (auto-created if absent) |

**Description template:**
```
h2. APF Stage: Sprint Planning

*Project:* my-saas-product
*Run ID:* a1b2c3d4
*Status:* Complete
*Duration:* 3m 26s

h3. Artifact
[View Sprint Plan|https://apf.local/artifacts/planning]

h3. Logs
[View Logs|https://apf.local/logs?stage=planning&run=a1b2c3d4]

h3. Summary
Sprint plan generated: 3 sprints, 24 user stories across 7 epics.

----
_Generated by Autonomous Product Factory_
```

### 5.3 Status Transitions

| APF Stage Status | Jira Issue Status |
|------------------|-------------------|
| `pending`        | `Backlog`         |
| `running`        | `In Progress`     |
| `awaiting`       | `In Review`       |
| `complete`       | `Done`            |
| `failed`         | `Blocked`         |
| `skipped`        | `Won't Do`        |

Jira workflow transitions are triggered via the API. The APF connector maps to standard Jira Software workflow transitions. If a transition is unavailable (non-standard workflow), the bot logs a warning and leaves the status unchanged.

### 5.4 PR Link Attachment

When the `coding` stage completes and produces a pull request:
- The PR URL is added to the Jira issue for the `review` stage as a **remote issue link** with relationship type "is reviewed in".
- The PR URL is also posted as a comment on the `coding` stage Jira issue.
- If GitHub/GitLab integration is separately configured, a Jira Smart Commit comment is appended to the commit message: `SAAS-42 #comment APF generated this PR`.

### 5.5 Error Handling

| Condition                  | Behavior                                                               |
|----------------------------|------------------------------------------------------------------------|
| Jira API unreachable       | Log error; queue ticket creation; retry with exponential backoff       |
| Invalid project key        | Log error; skip ticket creation; send Slack notification if enabled    |
| Transition not found       | Log warning; leave status unchanged; continue pipeline                 |
| Duplicate ticket detected  | Update existing ticket instead of creating a new one                   |

---

## 6. Confluence Bot UX

### 6.1 Page Creation and Update Behavior

A Confluence page is created (or updated if it already exists) when a stage produces an artifact.

**Trigger:** Stage status transitions to `complete` and an artifact file is present.
**Update behavior:** If a page for this stage/run already exists, its content is replaced. The previous version is preserved in Confluence page history.

### 6.2 Page Hierarchy

```
<Space Root>
└── APF Artifacts                         ← Parent page (auto-created)
    └── my-saas-product                   ← Project page (auto-created)
        └── Run: a1b2c3d4 (2026-03-23)    ← Run page (auto-created)
            ├── Idea Intake
            ├── PRD Generation
            ├── Architecture Design
            ├── UX Specification
            ├── Sprint Planning
            ├── Code Review Report
            └── Test Results
```

### 6.3 Page Metadata

| Confluence Field | Value                                           |
|------------------|-------------------------------------------------|
| **Title**        | `<Stage Display Name> — <Project> (run: <id>)` |
| **Labels**       | `apf`, `apf-<stage_id>`, `apf-<project>`        |
| **Parent page**  | Run page (see hierarchy above)                  |
| **Author**       | APF service account                             |

### 6.4 Templating Approach

Each artifact type has a Confluence storage format template. The APF bot:

1. Converts the raw markdown artifact to Confluence Storage Format (XHTML).
2. Wraps it in a stage-specific template that adds a metadata header panel.
3. Posts or updates the page via the Confluence REST API.

**Metadata header panel (added to every page):**
```
┌─────────────────────────────────────────────────────────┐
│ ℹ️  Generated by Autonomous Product Factory              │
│  Project: my-saas-product  │  Run: a1b2c3d4             │
│  Stage: PRD Generation     │  Completed: 2026-03-23     │
│  [View in APF Dashboard]   │  [View Logs]               │
└─────────────────────────────────────────────────────────┘
```

Followed by the full artifact content.

### 6.5 Artifact-to-Page Mapping

| Stage            | Confluence Page Title           | Content                               |
|------------------|---------------------------------|---------------------------------------|
| `intake`         | Idea Intake                     | Extracted requirements and constraints |
| `prd`            | PRD Generation                  | Full PRD document                     |
| `architecture`   | Architecture Design             | Architecture doc + diagrams (as code) |
| `ux`             | UX Specification                | Full UX spec                          |
| `planning`       | Sprint Planning                 | Sprint plan, epics, stories           |
| `review`         | Code Review Report              | Review findings and recommendations   |
| `testing`        | Test Results                    | Test run summary and coverage report  |

Stages `coding` and `deployment` do not produce Confluence pages by default (code lives in the repository; deployment state lives in AWS).

### 6.6 Error Handling

| Condition                     | Behavior                                                        |
|-------------------------------|-----------------------------------------------------------------|
| Confluence API unreachable    | Queue page creation; retry with backoff; log warning            |
| Space key not found           | Log error; skip page creation; notify via Slack if enabled      |
| Parent page not found         | Auto-create the missing parent pages and retry                  |
| Markdown conversion failure   | Post raw markdown as a code block with a conversion error note  |

---

## 7. AWS Bot UX

### 7.1 Deployment Trigger Flow

The AWS connector is triggered when the `deployment` stage begins. The APF agent does not manage the full deployment autonomously; it triggers a pre-configured deployment target and monitors its status.

**Step-by-step trigger flow:**

1. `deployment` stage starts.
2. APF bot reads AWS connector configuration (region, role, target type, cluster/service).
3. APF bot assumes the configured IAM role via `sts:AssumeRole`.
4. Depending on target type, APF bot triggers the deployment:
   - **ECS:** Calls `ecs:UpdateService` to force a new deployment of the target service.
   - **Lambda:** Calls `lambda:UpdateFunctionCode` with the new artifact zip.
   - **Elastic Beanstalk:** Calls `elasticbeanstalk:CreateApplicationVersion` then `UpdateEnvironment`.
   - **S3 Static Site:** Syncs build output to the target S3 bucket and optionally invalidates a CloudFront distribution.
5. APF bot polls for deployment completion at 30-second intervals.
6. On success, stage transitions to `complete`.
7. On failure, stage transitions to `failed` with the AWS error message captured in logs.

### 7.2 Status Feedback Format

**During deployment (logs):**
```
[14:55:01 INFO ] deployment  Assuming IAM role arn:aws:iam::123456789012:role/apf-deploy-role
[14:55:02 INFO ] deployment  AssumeRole successful
[14:55:02 INFO ] deployment  Triggering ECS service update: my-app-cluster / my-app-service
[14:55:03 INFO ] deployment  Deployment initiated. Task definition revision: 42 → 43
[14:55:03 INFO ] deployment  Polling deployment status (every 30s)…
[14:55:33 INFO ] deployment  Running tasks: 1 / 2  (new revision: 1, old revision: 1)
[14:56:03 INFO ] deployment  Running tasks: 2 / 2  (new revision: 2, old revision: 0)
[14:56:04 INFO ] deployment  Deployment complete. Service stable.
```

**Dashboard Stage Card (deployment running):**
```
┌────────────────────────────────────┐
│ ● Deployment              running  │
│                                    │
│  Target: ECS (my-app-cluster)      │
│  Tasks:  ████████░░  2/2 healthy  │
│  Elapsed: 00:01:03                 │
│                                    │
│  [View Logs]                       │
└────────────────────────────────────┘
```

**Dashboard Stage Card (deployment complete):**
```
┌────────────────────────────────────┐
│ ✓ Deployment             complete  │
│                                    │
│  Target: ECS (my-app-cluster)      │
│  Duration: 00:01:04                │
│  Task def: revision 43             │
│                                    │
│  [View Logs]  [Open AWS Console ↗] │
└────────────────────────────────────┘
```

### 7.3 Required IAM Permissions

The IAM role configured in the connector must have the minimum permissions for the selected target type.

**ECS minimum policy:**
```json
{
  "Effect": "Allow",
  "Action": [
    "ecs:UpdateService",
    "ecs:DescribeServices",
    "ecs:DescribeTaskDefinition",
    "ecs:RegisterTaskDefinition"
  ],
  "Resource": "*"
}
```

**Lambda minimum policy:**
```json
{
  "Effect": "Allow",
  "Action": [
    "lambda:UpdateFunctionCode",
    "lambda:GetFunctionConfiguration"
  ],
  "Resource": "arn:aws:lambda:<region>:<account>:function:<function-name>"
}
```

### 7.4 Error Handling

| Condition                      | Behavior                                                              |
|-------------------------------|-----------------------------------------------------------------------|
| `AssumeRole` fails             | Stage fails immediately; error includes ARN and IAM diagnosis hint    |
| Deployment timeout (>30 min)   | Stage fails; logs include last ECS/Lambda event                       |
| ECS service not found          | Stage fails with actionable message: "Check cluster and service name in connector settings" |
| Deployment rollback detected   | Stage fails; logs include the AWS rollback reason                     |
| CloudFront invalidation fails  | Warning logged; deployment still marked complete (invalidation is non-blocking) |

---

## 8. User Flows

### 8.1 Flow: First-Time Setup and Pipeline Run

1. User installs APF: `pip install apf` or downloads the binary.
2. User runs `apf init` in a project directory.
3. APF prompts for project name, template, and connectors.
4. User selects Slack and Jira connectors; APF runs setup wizards for each.
5. APF writes `.apf.yml` and confirms: "Initialization complete."
6. User runs `apf run "A SaaS tool for customer feedback"`.
7. APF confirms the run started (run ID displayed).
8. User optionally runs `apf status --watch` to monitor progress in the terminal.
9. Pipeline runs autonomously through `intake`, `prd`, `architecture`, `ux`, `planning`, `coding`.
10. `review` stage completes and pipeline transitions to `awaiting` for approval.
11. User receives a Slack notification with Approve / Reject buttons.
12. User clicks "View Report" to review, then clicks "Approve" in Slack.
13. Pipeline resumes through `testing` and `deployment`.
14. User receives "Pipeline Complete" Slack notification with PR link.
15. User opens the PR link and merges.

---

### 8.2 Flow: Resume from a Failed Stage

1. `coding` stage fails due to LLM API timeout.
2. User receives Slack error notification.
3. User runs `apf logs coding` to inspect the error.
4. User identifies the cause (API quota exceeded); waits or resolves the issue.
5. User runs `apf run --from=coding` to retry from the failed stage.
6. Previous stage artifacts are preserved; only `coding` onward re-runs.
7. Pipeline completes successfully.

---

### 8.3 Flow: Connector Configuration Change

1. User opens the web dashboard and navigates to Connectors.
2. User clicks "Configure" on the Slack connector.
3. `ConnectorWizard` modal opens pre-populated with current values.
4. User updates the notification channel from `#apf-notifications` to `#eng-alerts`.
5. User clicks "Test" — APF sends a test message to `#eng-alerts`.
6. User confirms the message arrived and clicks "Save."
7. Dashboard shows "✓ Slack connector updated."

---

### 8.4 Flow: Rejecting a Stage and Re-Running

1. `review` stage completes. Pipeline enters `awaiting` state.
2. User reviews the code review report and finds a critical security issue.
3. User clicks "Reject" in the Approval Panel (web or Slack).
4. User types a reason: "Critical SQL injection vulnerability in user input handling."
5. Pipeline status updates to `failed` for the `review` stage.
6. Developer fixes the issue and pushes a new commit.
7. User runs `apf run --from=coding` to regenerate code and re-run the review.
8. New review is clean; user approves.
9. Pipeline continues to `testing` and `deployment`.

---

### 8.5 Flow: Web Dashboard Monitoring (No CLI)

1. User opens the APF web dashboard in a browser.
2. Dashboard shows the Pipeline Overview with all stage cards.
3. `planning` stage is running — user clicks the card to expand inline logs.
4. User sees real-time log lines appearing.
5. `planning` completes; card turns green. `coding` starts; card turns amber with spinner.
6. User navigates to Artifact Viewer > PRD Generation to read the generated PRD.
7. User notices a requirement is ambiguous; makes a note to review with the team.
8. `coding` completes; `review` enters `awaiting`. Approval Panel banner appears at the top of the dashboard.
9. User reviews the report inline, types a comment, and clicks "Approve."
10. Pipeline resumes. User watches the remaining stages complete.

---

## 9. Error States and Recovery Paths

### 9.1 Error Taxonomy

| Category             | Description                                                   |
|----------------------|---------------------------------------------------------------|
| **Configuration**    | Missing or invalid `.apf.yml`, bad connector credentials      |
| **Agent / LLM**      | API timeout, token limit exceeded, malformed output           |
| **Connector**        | External service unreachable, auth failure, rate limit        |
| **Approval timeout** | Human did not act within the configured approval window       |
| **Infrastructure**   | Disk full, network error, AWS deployment failure              |

### 9.2 Error State Specifications

**Configuration error (at startup):**
```
Error: Invalid .apf.yml — field 'stages' is missing.

  Validate your config:   apf init --force
  Edit manually:          .apf.yml
  Documentation:          https://apf.dev/docs/config
```

**LLM API timeout:**
```
Error: [coding] LLM API request timed out after 120s (attempt 3 of 3).

  This may be a transient issue. Try the following:
    1. Wait a few minutes and retry:  apf run --from=coding
    2. Check your API key quota:      apf connectors test llm
    3. View full logs:                apf logs coding
```

**Connector auth failure:**
```
Error: [Jira connector] Authentication failed — 401 Unauthorized.

  Your Jira API token may have expired or been revoked.
    Reconfigure:  apf connectors configure jira
    Disable:      apf connectors disable jira (pipeline will continue without Jira)
```

**Approval timeout:**
```
Warning: Stage "review" approval timed out after 24h.
  Stage has been marked as failed.

  To re-run from this stage:  apf run --from=review
  To extend the timeout:      edit 'approve_timeout' in .apf.yml
```

**AWS deployment failure:**
```
Error: [deployment] ECS deployment failed — service did not stabilize within 30 minutes.

  Last ECS event: "Task stopped: essential container exited with code 1"

  Steps to diagnose:
    1. View ECS logs in CloudWatch for service "my-app-service"
    2. Check the task definition for misconfiguration
    3. Fix the issue and retry:  apf run --from=deployment
    4. View APF logs:            apf logs deployment
```

### 9.3 Recovery Path Summary

| Error                       | Immediate action                    | User recovery step                        |
|-----------------------------|-------------------------------------|-------------------------------------------|
| Config invalid              | Pipeline does not start             | `apf init --force` or edit `.apf.yml`    |
| LLM timeout                 | Stage fails after retries           | `apf run --from=<stage>`                 |
| Connector auth failure      | Connector skipped with warning      | `apf connectors configure <name>`        |
| Approval timeout            | Stage fails                         | `apf run --from=<stage>`                 |
| AWS deploy failure          | Stage fails with AWS error captured | Fix infra; `apf run --from=deployment`   |
| Disk full                   | Pipeline paused; error logged       | Free disk space; `apf run --from=<stage>`|

---

## 10. Accessibility Notes

### 10.1 CLI Accessibility

- **Color independence:** Every status indicator that uses color also uses a text label or symbol. Status is never communicated by color alone (e.g., "✓ complete" not just green text).
- **`--no-color` flag:** Disables all ANSI codes for users with color vision deficiency or who pipe output to tools that don't handle ANSI.
- **`--plain` output mode:** Produces output suitable for screen readers and log parsers with no ANSI, no box-drawing characters, and consistent delimiters.
- **Spinner alternatives:** When `--no-color` is active, spinning animations are replaced with periodic text updates ("…still running…").

### 10.2 Web Dashboard Accessibility

- **WCAG 2.1 AA compliance target** for all interactive components.
- **Color + icon + text:** Status is communicated with all three — a colored badge, an icon (✓ ● ⚑ ✗ ○), and a text label. Never color alone.
- **Keyboard navigation:** All interactive elements (buttons, links, dropdowns, modals) are reachable and activatable via keyboard. Tab order follows visual reading order.
- **Focus management:** When a modal (e.g., `ApprovalPanel`, `ConnectorWizard`) opens, focus moves to the modal. When it closes, focus returns to the triggering element.
- **ARIA roles and labels:** All custom components use appropriate ARIA roles (`role="status"`, `role="dialog"`, `aria-live="polite"` for log streams, `aria-label` on icon-only buttons).
- **Live regions:** The `LogStream` component uses `aria-live="polite"` so screen reader users are informed of new log entries without the entire region being re-read.
- **Minimum tap targets:** All interactive elements are at least 44×44 CSS pixels on touch devices.
- **Text scaling:** UI layout remains functional at 200% browser text zoom without horizontal scrolling.
- **Reduced motion:** Animations (spinners, progress rings, pulsing indicators) respect the `prefers-reduced-motion` media query and fall back to static indicators.
- **Contrast ratios:** All text meets minimum contrast ratios: 4.5:1 for body text, 3:1 for large text and UI components.

### 10.3 Slack Accessibility

- All Block Kit messages include plain-text fallback fields for clients that do not support Block Kit.
- Approval buttons include descriptive `action_id` values and `accessibility_label` fields (e.g., "Approve Code Review stage" rather than just "Approve").
- Status emoji are always accompanied by text labels in the same message block.

---

*End of UX Specification*
