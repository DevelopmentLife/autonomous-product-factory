#!/usr/bin/env bash
# =============================================================================
# run-tests.sh
# Run the full APF test suite across all packages with coverage aggregation.
# Usage: bash scripts/run-tests.sh [options]
#   --python-only    Run only Python tests
#   --frontend-only  Run only frontend tests
#   --no-coverage    Skip coverage reporting
#   --fast           Skip slow integration tests (mark with @pytest.mark.slow)
#   --watch          Run in watch mode (Python only)
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
RUN_PYTHON=true
RUN_FRONTEND=true
WITH_COVERAGE=true
FAST=false
WATCH=false
EXIT_CODE=0

# ---------------------------------------------------------------------------
# Arg parsing
# ---------------------------------------------------------------------------
for arg in "$@"; do
  case "$arg" in
    --python-only)    RUN_FRONTEND=false ;;
    --frontend-only)  RUN_PYTHON=false ;;
    --no-coverage)    WITH_COVERAGE=false ;;
    --fast)           FAST=true ;;
    --watch)          WATCH=true ;;
    --help|-h)
      grep '^#' "$0" | grep -v '^#!/' | sed 's/^# *//'
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 1
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

log_section() { echo -e "\n${BOLD}${CYAN}==> $*${RESET}"; }
log_success() { echo -e "${GREEN}[PASS]${RESET} $*"; }
log_failure() { echo -e "${RED}[FAIL]${RESET} $*"; }

# ---------------------------------------------------------------------------
# Python tests
# ---------------------------------------------------------------------------
run_python_tests() {
  log_section "Python Tests"
  cd "$REPO_ROOT"

  local pytest_args=(-q --tb=short)

  if $WITH_COVERAGE; then
    pytest_args+=(
      --cov
      --cov-report=term-missing
      --cov-report=xml:coverage-python.xml
      --cov-report=html:htmlcov
      --cov-fail-under=80
    )
  fi

  if $FAST; then
    pytest_args+=(-m "not slow")
    echo -e "${YELLOW}  Skipping slow tests (--fast)${RESET}"
  fi

  if $WATCH; then
    echo "  Starting pytest-watch (Ctrl+C to stop)..."
    uv run ptw -- "${pytest_args[@]}"
  else
    if uv run pytest "${pytest_args[@]}"; then
      log_success "Python tests passed."
    else
      log_failure "Python tests FAILED."
      EXIT_CODE=1
    fi
  fi
}

# ---------------------------------------------------------------------------
# Frontend tests
# ---------------------------------------------------------------------------
run_frontend_tests() {
  log_section "Frontend Tests (Vitest)"
  cd "$REPO_ROOT"

  local vitest_args=(--run --reporter=verbose)

  if $WITH_COVERAGE; then
    vitest_args+=(--coverage)
  fi

  if pnpm --filter dashboard test "${vitest_args[@]}"; then
    log_success "Frontend tests passed."
  else
    log_failure "Frontend tests FAILED."
    EXIT_CODE=1
  fi
}

# ---------------------------------------------------------------------------
# Coverage aggregation
# ---------------------------------------------------------------------------
print_coverage_summary() {
  if ! $WITH_COVERAGE; then
    return
  fi

  log_section "Coverage Summary"

  if [ -f "${REPO_ROOT}/coverage-python.xml" ]; then
    echo "  Python coverage report: htmlcov/index.html"
    echo "  Python XML report:      coverage-python.xml"
  fi

  local dashboard_coverage="${REPO_ROOT}/services/dashboard/coverage"
  if [ -d "$dashboard_coverage" ]; then
    echo "  Frontend coverage:      services/dashboard/coverage/index.html"
  fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  local start_time
  start_time=$(date +%s)

  echo -e "${BOLD}${CYAN}APF Test Suite${RESET}"
  echo "Repository: ${REPO_ROOT}"
  echo "Python: $RUN_PYTHON | Frontend: $RUN_FRONTEND | Coverage: $WITH_COVERAGE | Fast: $FAST"

  if $RUN_PYTHON; then
    run_python_tests
  fi

  if $RUN_FRONTEND; then
    run_frontend_tests
  fi

  print_coverage_summary

  local end_time elapsed
  end_time=$(date +%s)
  elapsed=$((end_time - start_time))

  echo ""
  if [ "$EXIT_CODE" -eq 0 ]; then
    echo -e "${BOLD}${GREEN}All tests passed in ${elapsed}s.${RESET}"
  else
    echo -e "${BOLD}${RED}Some tests FAILED (${elapsed}s). See output above.${RESET}"
  fi

  exit "$EXIT_CODE"
}

main
