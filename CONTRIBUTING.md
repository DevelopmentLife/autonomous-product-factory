# Contributing to APF

Thank you for your interest in contributing to the Autonomous Product Factory (APF). This guide covers everything you need to get started.

## Table of Contents

1. [Development Setup](#development-setup)
2. [Repository Structure](#repository-structure)
3. [Branching Strategy](#branching-strategy)
4. [Commit Format](#commit-format)
5. [Pull Request Process](#pull-request-process)
6. [Code Style](#code-style)
7. [Testing](#testing)
8. [Documentation](#documentation)
9. [Release Process](#release-process)

---

## Development Setup

### Prerequisites

| Tool | Version | Installation |
|------|---------|--------------|
| Python | 3.12+ | [python.org](https://www.python.org/) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | 20+ | [nodejs.org](https://nodejs.org/) |
| pnpm | 9.x | `npm install -g pnpm@9` |
| Docker | 24+ | [docs.docker.com](https://docs.docker.com/get-docker/) |
| Docker Compose | v2 | bundled with Docker Desktop |
| git | 2.40+ | [git-scm.com](https://git-scm.com/) |

### One-command Setup

```bash
git clone https://github.com/apf-project/apf.git
cd apf
bash scripts/setup-dev.sh
```

This script will:

1. Verify all prerequisites are installed
2. Install Python dependencies (`uv sync --all-packages`)
3. Install Node dependencies (`pnpm install`)
4. Copy `deploy/.env.example` to `deploy/.env` with a generated secret key
5. Install pre-commit hooks
6. Start infrastructure services (postgres, redis, minio) via Docker Compose
7. Run database migrations

### Manual Setup

If you prefer to run each step manually:

```bash
# Install Python deps
uv sync --all-packages --frozen

# Install Node deps
pnpm install --frozen-lockfile

# Copy and configure env
cp deploy/.env.example deploy/.env
# Edit deploy/.env and fill in required secrets

# Start infrastructure
docker compose -f deploy/docker-compose.yml up -d postgres redis minio

# Run migrations
make migrate

# Install pre-commit hooks
uv run pre-commit install --install-hooks
```

---

## Repository Structure

```
apf/
├── packages/               # Shared Python packages (workspace members)
│   ├── agent-core/         # Core agent abstractions and base classes
│   ├── db/                 # Database models, migrations (Alembic), repositories
│   └── event-bus/          # Event bus abstractions and implementations
├── services/               # Independent deployable services
│   ├── orchestrator/       # Central API + task orchestration (FastAPI)
│   ├── agent-runner/       # Agent execution workers
│   ├── artifact-store/     # Artifact storage API
│   ├── dashboard/          # React/TypeScript frontend
│   ├── github-integration/ # GitHub App webhook handler
│   ├── slack-connector/    # Slack Bot connector
│   ├── jira-connector/     # Jira integration
│   ├── confluence-connector/
│   └── aws-connector/      # AWS ECS task launcher
├── cli/                    # apf-cli Python package
├── deploy/                 # Docker Compose + env templates
├── scripts/                # Developer convenience scripts
├── docs/                   # Architecture docs, ADRs
└── .github/                # CI/CD workflows, PR templates
```

---

## Branching Strategy

| Branch pattern | Purpose |
|----------------|---------|
| `main` | Production-ready code. Protected — no direct pushes. |
| `feature/<short-description>` | New features |
| `fix/<short-description>` | Bug fixes |
| `docs/<short-description>` | Documentation-only changes |
| `chore/<short-description>` | Dependency updates, tooling, CI |
| `refactor/<short-description>` | Code refactoring without functional change |

**Rules:**

- Branch from `main`.
- Keep branches short-lived (ideally < 1 week).
- Delete branches after merging.
- Rebase onto `main` before opening a PR (not merge commits).

---

## Commit Format

APF uses [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

```
<type>(<scope>): <short summary>

[optional body]

[optional footer(s)]
```

### Types

| Type | When to use |
|------|-------------|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no logic change |
| `refactor` | Code restructure, no feature/fix |
| `perf` | Performance improvement |
| `test` | Adding or fixing tests |
| `chore` | Build process, tooling, dependencies |
| `ci` | CI/CD changes |
| `revert` | Reverting a previous commit |

### Scopes (optional)

Use the service or package name as scope: `orchestrator`, `agent-runner`, `db`, `agent-core`, `cli`, `dashboard`, `github`, `slack`, etc.

### Examples

```
feat(orchestrator): add task priority queue

fix(agent-runner): handle timeout errors in LLM calls

docs(contributing): add branching strategy section

chore(deps): bump anthropic sdk to 0.28.0

test(db): add repository integration tests for UserModel
```

### Breaking Changes

Add `BREAKING CHANGE:` in the footer or append `!` after the type:

```
feat(db)!: rename user_id column to id in all tables

BREAKING CHANGE: Existing migrations must be re-run from scratch.
```

---

## Pull Request Process

1. **Open a draft PR early** to signal work in progress and get early feedback.
2. **Fill in the PR template** completely — summary, type of change, testing checklist.
3. **Keep PRs focused** — one logical change per PR. Prefer smaller PRs.
4. **Ensure all CI checks pass** before requesting review.
5. **Request review** from at least one member of `@apf-project/core-team`.
6. **Address all review comments** before merging.
7. **Squash-merge** into `main` with a conventional commit message.
8. **Delete the branch** after merging.

### PR Size Guidelines

| Size | Lines changed | Guidance |
|------|--------------|---------|
| XS | < 50 | Ideal |
| S | 50–200 | Good |
| M | 200–500 | Acceptable; consider splitting |
| L | 500–1000 | Split if possible |
| XL | > 1000 | Requires justification in PR description |

---

## Code Style

### Python

- Formatter: **ruff format** (configured in `pyproject.toml`, line length 100)
- Linter: **ruff** with rules E, F, I, N, UP, B, SIM
- Type checker: **mypy** strict mode
- Style: follow PEP 8; prefer dataclasses or Pydantic models over plain dicts

Run all Python checks:

```bash
make lint-python
```

Auto-fix formatting:

```bash
uv run ruff format .
uv run ruff check --fix .
```

### TypeScript / React

- Formatter: **Prettier** (config in `services/dashboard/.prettierrc`)
- Linter: **ESLint** with TypeScript plugin
- Style: functional components, React hooks, no class components

Run all frontend checks:

```bash
make lint-frontend
```

### General

- No trailing whitespace
- Unix line endings (LF)
- UTF-8 encoding
- Files must end with a newline
- These are enforced by `.editorconfig` and pre-commit hooks

---

## Testing

### Running Tests

```bash
make test           # Full suite (Python + frontend)
make test-python    # Python only
make test-frontend  # Frontend only
```

### Writing Tests

**Python:**

- Place tests in a `tests/` directory within each package or service
- Use `pytest` with `asyncio_mode = "auto"` for async tests
- Use `pytest-mock` for mocking; avoid `unittest.mock` directly
- Integration tests that require external services should be marked `@pytest.mark.slow`
- Aim for 80%+ coverage; 100% is not required but aim for critical paths

**Frontend:**

- Use **Vitest** + **React Testing Library**
- Test behaviour, not implementation
- Snapshot tests should be minimised; prefer explicit assertions

### Test Naming

```python
def test_<unit>_<scenario>_<expected_outcome>():
    # Arrange
    # Act
    # Assert
```

Example: `test_user_repository_create_raises_on_duplicate_email`

---

## Documentation

### Code Documentation

- All public Python functions/classes must have docstrings (Google style)
- TypeScript public functions should have JSDoc comments for non-obvious APIs
- Complex logic must have inline comments explaining the **why**, not the **what**

### Architecture Decision Records (ADRs)

When making significant architectural decisions, create an ADR in `docs/adrs/`:

```
docs/adrs/
  0001-use-postgresql-as-primary-db.md
  0002-event-driven-agent-coordination.md
```

Use the template at `docs/adrs/TEMPLATE.md`.

### CHANGELOG

Update `CHANGELOG.md` under `[Unreleased]` for every PR that introduces a user-visible change.

---

## Release Process

Releases are managed by maintainers:

1. Update `CHANGELOG.md` — move `[Unreleased]` items under the new version heading
2. Bump versions in relevant `pyproject.toml` files
3. Commit: `chore(release): bump version to v1.2.3`
4. Tag: `git tag v1.2.3 && git push origin v1.2.3`
5. The `release.yml` workflow handles Docker image publishing, PyPI publish, and GitHub Release creation automatically

---

## Getting Help

- Open a [GitHub Discussion](https://github.com/apf-project/apf/discussions) for questions
- Open a [GitHub Issue](https://github.com/apf-project/apf/issues) for bugs or feature requests
- Tag `@apf-project/core-team` for urgent matters
