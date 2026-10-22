#!/usr/bin/env bash
# Build and (re)start Swap on the VPS. Run it from the clone (~/swap):
#
#   ./deploy/vps.sh           build and redeploy
#   ./deploy/vps.sh --pull    git pull first (the usual redeploy)
#
# In order: pull, build (the old containers keep serving), dump the database if it
# has a schema, migrate, recreate api and worker, wait for both to be healthy.
# Caddy holds requests while the api restarts (deploy/Caddyfile-swap.caddy), so a
# deploy looks like a slow request, not a 502.
#
# Rollback: `git checkout <previous> && ./deploy/vps.sh`, plus restoring the newest
# dump in backups/ if a migration ran (ADR-0011).
set -euo pipefail
cd "$(dirname "$0")/.."

# An absolute --env-file, deliberately. Compose takes its project directory from the
# -f file's directory (deploy/), so without it ${POSTGRES_PASSWORD} would be read from
# deploy/.env, which doesn't exist.
COMPOSE=(sudo docker compose --env-file "$PWD/.env" -f deploy/docker-compose.vps.yml)
BACKUPS=backups
KEEP_DUMPS=5

if [ ! -f .env ]; then
    echo "no .env: copy .env.example to .env and fill it in" >&2
    exit 1
fi
chmod 600 .env

if [ "${1:-}" = "--pull" ]; then
    git pull --ff-only
fi
echo "deploying $(git log -1 --format='%h %s')"

# The commit is the release in error reports (ADR-0025).
"${COMPOSE[@]}" build --build-arg SENTRY_RELEASE="$(git rev-parse --short HEAD)"
"${COMPOSE[@]}" up -d --wait db

# A dump before every migration. It survives a bad migration, not a lost server; the
# off-box backups are phase 1's slice 7.
has_schema=$("${COMPOSE[@]}" exec -T db \
    psql -U swap -d swap -tAc "SELECT 1 FROM pg_tables WHERE tablename = 'alembic_version'")
if [ -n "$has_schema" ]; then
    mkdir -p "$BACKUPS"
    dump="$BACKUPS/swap-$(date -u +%Y%m%dT%H%M%SZ)-$(git rev-parse --short HEAD).sql.gz"
    "${COMPOSE[@]}" exec -T db pg_dump -U swap -d swap | gzip > "$dump"
    gzip -t "$dump"
    echo "dumped the database to $dump"
    # shellcheck disable=SC2012  # our own file names, no spaces
    ls -1t "$BACKUPS"/swap-*.sql.gz | tail -n +$((KEEP_DUMPS + 1)) | xargs -r rm --
fi

"${COMPOSE[@]}" run --rm migrate
"${COMPOSE[@]}" up -d --wait --no-deps --force-recreate api worker
"${COMPOSE[@]}" ps
