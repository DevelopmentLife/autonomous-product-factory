# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2024-01-01

### Added

- Initial repository scaffold: root `pyproject.toml` (uv workspace), `package.json` (pnpm workspace)
- CI/CD: GitHub Actions workflows for lint, test, Docker build (`ci.yml`) and release (`release.yml`)
- Docker Compose stack: postgres, redis, minio, orchestrator, agent-runner, artifact-store, dashboard, and optional connector profiles (github, slack, jira, confluence, aws)
- Developer override compose file (`docker-compose.dev.yml`) with source-mount hot-reload
- Environment variable template (`deploy/.env.example`) covering all services
- Database initialisation script (`deploy/init-db.sh`) — waits for Postgres, runs Alembic migrations, seeds admin user
- Pre-commit hooks: ruff, mypy, prettier, shellcheck, detect-secrets, and general file-hygiene hooks
- Comprehensive `.gitignore` for Python, Node, Docker, and IDE files
- `.editorconfig` for consistent formatting across Python, TypeScript, YAML, and shell
- `Makefile` with targets: `install`, `dev`, `test`, `lint`, `build`, `clean`, `migrate`, `generate-openapi`
- Developer setup script (`scripts/setup-dev.sh`) — checks prerequisites, installs deps, copies env, starts infra, runs migrations
- Test runner script (`scripts/run-tests.sh`) with coverage aggregation and `--fast`/`--watch` flags
- Apache 2.0 LICENSE
- GitHub PR template, CODEOWNERS, and CONTRIBUTING guide
- APF self-configuration example (`.apf/config.yaml.example`)

[Unreleased]: https://github.com/apf-project/apf/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/apf-project/apf/releases/tag/v0.1.0
