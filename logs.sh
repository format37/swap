#!/usr/bin/env bash
# Follow the local stack's logs, or one service's: ./logs.sh worker
set -euo pipefail
cd "$(dirname "$0")"
docker compose logs -f -t "$@"
