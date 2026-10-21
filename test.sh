#!/usr/bin/env bash
# Run the suites.
#
# The backend suite needs real Postgres. It uses the compose db on 127.0.0.1:5436
# and a `swap_test` database, which tests/conftest.py creates and migrates from
# scratch on every run.
#
#   ./test.sh                  everything
#   ./test.sh backend [args]   pytest only; extra args go to pytest
#   ./test.sh frontend         vitest only
set -euo pipefail
cd "$(dirname "$0")"

# uv 0.13 or newer (backend/pyproject.toml requires it). On a machine with an older
# one: UV="uvx --from uv==0.13.4 uv" ./test.sh
UV=${UV:-uv}

run_backend() {
    docker compose up -d --wait db
    # Word splitting is wanted: $UV may be a whole command.
    # shellcheck disable=SC2086
    (cd backend && $UV run pytest "$@")
}

run_frontend() {
    (cd frontend && npx vitest run)
}

target="${1:-all}"
[ $# -gt 0 ] && shift || true
case "$target" in
    backend)  run_backend "$@" ;;
    frontend) run_frontend ;;
    all)      run_backend && run_frontend ;;
    *)        echo "usage: ./test.sh [all|backend|frontend] [pytest args...]" >&2; exit 2 ;;
esac
