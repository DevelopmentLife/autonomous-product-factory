#!/usr/bin/env bash
# =============================================================================
# init-db.sh
# Wait for PostgreSQL to be ready, run Alembic migrations, and seed the
# default admin user. Intended to run inside the orchestrator container on
# first start, or as a Docker init script.
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration (override via environment variables)
# ---------------------------------------------------------------------------
DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://apf:apf_dev_password@postgres:5432/apf}"
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-apf}"
POSTGRES_DB="${POSTGRES_DB:-apf}"

ADMIN_EMAIL="${APF_ADMIN_EMAIL:-admin@apf.local}"
ADMIN_PASSWORD="${APF_ADMIN_PASSWORD:-}"
MAX_RETRIES=30
RETRY_INTERVAL=2

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log() {
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"
}

die() {
  log "ERROR: $*" >&2
  exit 1
}

# ---------------------------------------------------------------------------
# Wait for PostgreSQL
# ---------------------------------------------------------------------------
wait_for_postgres() {
  log "Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT}..."
  local attempt=0
  until pg_isready -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -q; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge "$MAX_RETRIES" ]; then
      die "PostgreSQL did not become ready after ${MAX_RETRIES} attempts."
    fi
    log "  Attempt ${attempt}/${MAX_RETRIES} — retrying in ${RETRY_INTERVAL}s..."
    sleep "${RETRY_INTERVAL}"
  done
  log "PostgreSQL is ready."
}

# ---------------------------------------------------------------------------
# Run Alembic migrations
# ---------------------------------------------------------------------------
run_migrations() {
  log "Running Alembic migrations..."
  if command -v uv &>/dev/null; then
    uv run alembic -c packages/db/alembic.ini upgrade head
  else
    alembic -c packages/db/alembic.ini upgrade head
  fi
  log "Migrations complete."
}

# ---------------------------------------------------------------------------
# Seed default admin user
# ---------------------------------------------------------------------------
seed_admin_user() {
  if [ -z "${ADMIN_PASSWORD}" ]; then
    log "APF_ADMIN_PASSWORD is not set — generating a random password."
    ADMIN_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
    log "Generated admin password: ${ADMIN_PASSWORD}"
    log "IMPORTANT: Save this password now — it will not be shown again."
  fi

  log "Seeding default admin user: ${ADMIN_EMAIL}"

  python3 - <<PYTHON
import asyncio
import os
import sys

async def seed():
    try:
        from apf_db.session import get_async_session
        from apf_db.repositories.user import UserRepository
        from apf_db.models.user import UserCreate, UserRole

        async with get_async_session() as session:
            repo = UserRepository(session)
            existing = await repo.get_by_email("${ADMIN_EMAIL}")
            if existing:
                print(f"Admin user '${ADMIN_EMAIL}' already exists — skipping seed.")
                return
            user = await repo.create(
                UserCreate(
                    email="${ADMIN_EMAIL}",
                    password="${ADMIN_PASSWORD}",
                    full_name="APF Administrator",
                    role=UserRole.ADMIN,
                    is_active=True,
                )
            )
            await session.commit()
            print(f"Created admin user: {user.email} (id={user.id})")
    except ImportError as exc:
        print(f"WARNING: Could not import DB modules ({exc}). Skipping seed.")
        sys.exit(0)
    except Exception as exc:
        print(f"ERROR during seed: {exc}", file=sys.stderr)
        sys.exit(1)

asyncio.run(seed())
PYTHON

  log "Admin seed complete."
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  log "=== APF Database Initialisation ==="
  wait_for_postgres
  run_migrations
  seed_admin_user
  log "=== Initialisation complete ==="
}

main "$@"
