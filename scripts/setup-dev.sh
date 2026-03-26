#!/usr/bin/env bash
# =============================================================================
# setup-dev.sh
# One-command developer environment setup for APF.
# Run from the repository root: bash scripts/setup-dev.sh
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log_info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
log_success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
die()         { log_error "$*"; exit 1; }

# ---------------------------------------------------------------------------
# Prerequisites check
# ---------------------------------------------------------------------------
check_prerequisites() {
  log_info "Checking prerequisites..."
  local missing=()

  # uv
  if command -v uv &>/dev/null; then
    log_success "uv $(uv --version | head -1)"
  else
    missing+=("uv (https://docs.astral.sh/uv/getting-started/installation/)")
  fi

  # pnpm
  if command -v pnpm &>/dev/null; then
    log_success "pnpm $(pnpm --version)"
  else
    missing+=("pnpm (https://pnpm.io/installation)")
  fi

  # docker
  if command -v docker &>/dev/null; then
    log_success "docker $(docker --version)"
  else
    missing+=("docker (https://docs.docker.com/get-docker/)")
  fi

  # docker compose (v2 plugin)
  if docker compose version &>/dev/null 2>&1; then
    log_success "docker compose $(docker compose version --short 2>/dev/null || echo 'v2')"
  else
    missing+=("docker compose v2 plugin (https://docs.docker.com/compose/install/)")
  fi

  # git
  if command -v git &>/dev/null; then
    log_success "git $(git --version | awk '{print $3}')"
  else
    missing+=("git (https://git-scm.com/downloads)")
  fi

  if [ ${#missing[@]} -gt 0 ]; then
    log_error "The following prerequisites are missing:"
    for item in "${missing[@]}"; do
      echo -e "  ${RED}✗${RESET} $item"
    done
    die "Please install the missing tools and re-run this script."
  fi

  log_success "All prerequisites found."
}

# ---------------------------------------------------------------------------
# Python dependencies
# ---------------------------------------------------------------------------
install_python_deps() {
  log_info "Installing Python dependencies with uv..."
  cd "$REPO_ROOT"
  uv sync --all-packages --frozen
  log_success "Python dependencies installed."
}

# ---------------------------------------------------------------------------
# Node dependencies
# ---------------------------------------------------------------------------
install_node_deps() {
  log_info "Installing Node dependencies with pnpm..."
  cd "$REPO_ROOT"
  pnpm install --frozen-lockfile
  log_success "Node dependencies installed."
}

# ---------------------------------------------------------------------------
# Environment file
# ---------------------------------------------------------------------------
setup_env() {
  local env_file="${REPO_ROOT}/deploy/.env"
  local example_file="${REPO_ROOT}/deploy/.env.example"

  if [ -f "$env_file" ]; then
    log_warn "deploy/.env already exists — skipping copy. Review it manually."
  else
    log_info "Copying deploy/.env.example to deploy/.env..."
    cp "$example_file" "$env_file"
    # Generate a random secret key
    local secret_key
    secret_key="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
    sed -i "s|CHANGE_ME_generate_a_secure_random_key_at_least_32_chars|${secret_key}|" "$env_file"
    log_success "Created deploy/.env with a generated APF_SECRET_KEY."
    log_warn "Open deploy/.env and fill in any required API keys before starting services."
  fi
}

# ---------------------------------------------------------------------------
# Pre-commit hooks
# ---------------------------------------------------------------------------
install_precommit() {
  log_info "Installing pre-commit hooks..."
  cd "$REPO_ROOT"
  if git rev-parse --git-dir &>/dev/null; then
    uv run pre-commit install --install-hooks
    log_success "Pre-commit hooks installed."
  else
    log_warn "Not inside a git repository — skipping pre-commit install."
  fi
}

# ---------------------------------------------------------------------------
# Docker services
# ---------------------------------------------------------------------------
start_infrastructure() {
  log_info "Starting infrastructure services (postgres, redis, minio)..."
  cd "${REPO_ROOT}/deploy"
  docker compose up -d postgres redis minio
  log_success "Infrastructure services started."
}

wait_for_health() {
  log_info "Waiting for services to pass health checks..."
  local attempts=0
  local max_attempts=30

  until docker compose -f "${REPO_ROOT}/deploy/docker-compose.yml" ps postgres | grep -q "healthy"; do
    attempts=$((attempts + 1))
    if [ "$attempts" -ge "$max_attempts" ]; then
      die "PostgreSQL did not become healthy in time. Check: docker compose -f deploy/docker-compose.yml logs postgres"
    fi
    sleep 2
  done

  log_success "PostgreSQL is healthy."
}

# ---------------------------------------------------------------------------
# Database migrations
# ---------------------------------------------------------------------------
run_migrations() {
  log_info "Running database migrations..."
  cd "$REPO_ROOT"
  if uv run alembic -c packages/db/alembic.ini upgrade head; then
    log_success "Migrations applied."
  else
    log_warn "Could not run migrations. Run manually once packages/db is initialised: make migrate"
  fi
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print_summary() {
  echo ""
  echo -e "${BOLD}${GREEN}============================${RESET}"
  echo -e "${BOLD}${GREEN}  APF Dev Setup Complete!${RESET}"
  echo -e "${BOLD}${GREEN}============================${RESET}"
  echo ""
  echo -e "  ${CYAN}Services:${RESET}"
  echo -e "    PostgreSQL   → localhost:5432"
  echo -e "    Redis        → localhost:6379"
  echo -e "    MinIO        → http://localhost:9000  (console: http://localhost:9001)"
  echo ""
  echo -e "  ${CYAN}Next steps:${RESET}"
  echo -e "    1. Fill in API keys in ${YELLOW}deploy/.env${RESET}"
  echo -e "    2. ${BOLD}make dev${RESET}  — start all services with hot-reload"
  echo -e "    3. ${BOLD}make test${RESET} — run the full test suite"
  echo -e "    4. ${BOLD}make lint${RESET} — run all linters"
  echo ""
  echo -e "  Run ${BOLD}make help${RESET} for all available commands."
  echo ""
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  echo ""
  echo -e "${BOLD}${CYAN}APF Developer Environment Setup${RESET}"
  echo -e "${CYAN}Repository: ${REPO_ROOT}${RESET}"
  echo ""

  check_prerequisites
  install_python_deps
  install_node_deps
  setup_env
  install_precommit
  start_infrastructure
  wait_for_health
  run_migrations
  print_summary
}

main "$@"
