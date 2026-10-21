# Deploying Swap to the VPS

Production runs on the owner's VPS. The shared Caddy sits in front (ADR-0001), and
the bot goes through the VPS's own Bot API server and the owner's relay (ADR-0008).
A deploy needs the owner's go in the current session (CLAUDE.md).

## Routine redeploy

    cd ~/swap && ./deploy/vps.sh --pull

It builds on the box and dumps the database into `backups/`. Then it migrates,
recreates api and worker, and waits until both are healthy.

To roll back, run `git checkout <previous> && ./deploy/vps.sh`. If a migration ran,
also restore the newest dump:

    gunzip -c backups/<dump>.sql.gz | sudo docker exec -i swap-db psql -U swap -d swap

## First deploy

Done once, on 2026-10-21. The steps stay here as the record. Backups of the shared
files from that day sit beside them: `Caddyfile.bak-20261021-swap` and
`bots.json.bak-20261021-swap`.

1. **DNS.** An A record for `swap.latentstate.dev` pointing at the VPS, DNS only
   (grey cloud).
2. **Clone.** `git clone https://github.com/format37/swap.git ~/swap`.
3. **Environment.** Create `~/swap/.env` from `.env.example`, mode 600, with:
   - `APP_ENV=prod` and `LOG_FORMAT=json`;
   - `TELEGRAM_BOT_TOKEN`;
   - a long random `POSTGRES_PASSWORD` in hex, because it goes into a URL.

   Leave `TELEGRAM_API_BASE` out: compose gives it to the worker alone.
4. **Deploy.** `./deploy/vps.sh`.
5. **The relay** (format37/telegram_bot), once the worker is listening:
   - The bot must be logged out of the cloud Bot API first. The owner did that on
     2026-10-21.
   - Back up `~/telegram_bot/bots.json`.
   - Add `"PEERTOPEERSWAPBOT": {"TOKEN": "…", "PORT": 8707, "active": 1}` with a
     JSON-aware tool that keeps the file's inode.
   - Run `sudo docker restart bots_server_telegram`. This re-sets every bot's webhook.
   - Check each bot's `getWebhookInfo` through `127.0.0.1:8081`.
6. **Caddy.**
   - Back up `~/reverse-proxy/Caddyfile`.
   - Append the block: `cat deploy/Caddyfile-swap.caddy >> ~/reverse-proxy/Caddyfile`.
   - Run `caddy validate`, then `caddy reload`.
   - Probe every site on the box before and after.

## Checks

- `curl -s https://swap.latentstate.dev/healthz` checks the api, the database and the
  worker's heartbeat.
- `curl -s 127.0.0.1:8707/healthz`, on the box, checks the worker. It should say
  `"telegram": true`.
- `sudo docker logs -f swap-worker` (or `swap-api`) follows the logs.
