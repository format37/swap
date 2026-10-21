#!/usr/bin/env bash
# Build and (re)start the local stack: Caddy on http://127.0.0.1:8030, api, worker,
# Postgres. Migrations run on every start.
#
#   ./compose.sh            build what changed and start
#   ./compose.sh --fresh    also drop the database volume
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f .env ]; then
    cp .env.example .env
    chmod 600 .env
    echo "created .env from .env.example: fill in TELEGRAM_BOT_TOKEN"
fi
if [ "${1:-}" = "--fresh" ]; then
    docker compose down -v
    shift
fi

docker compose up -d --build --wait "$@"

echo
echo "app    -> http://127.0.0.1:8030   (outside Telegram it shows the stub;"
echo "          CLAUDE.md says how to open it with a signed launch)"
echo "health -> curl -s http://127.0.0.1:8030/healthz"
