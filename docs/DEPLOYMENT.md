# Deployment and recovery basics

## Central backend host (Ubuntu, Docker)

1. Copy `.env.example` to `.env` and set `POSTGRES_PASSWORD` and the
   `ALERT_MANAGER_ADMIN_*` bootstrap credentials.
2. Run `docker compose up -d --build`. This starts PostgreSQL (with a named
   volume for persistence), the backend (API on 8000, agent ingest on 7754),
   and the web UI (on 8080, proxied through Apache).
3. Wait for all three services to report healthy: `docker compose ps`.
4. Create the first administrator:
   `docker compose exec backend python -m app.bootstrap`
   (reads `ALERT_MANAGER_ADMIN_USERNAME` / `ALERT_MANAGER_ADMIN_PASSWORD` from
   the backend container's environment — pass them with `-e` if not already
   set in `.env`/`docker-compose.yml`).
5. Open the web UI and sign in with that account.

Open tcp/7754 only to the network ranges that host Suricata agents, and
tcp/8080 (or your reverse proxy in front of it) to analysts.

## Suricata agent host (Ubuntu)

1. Build the agent: `cargo build --release --manifest-path agent/Cargo.toml`.
2. Copy `agent/.env.example` to a location the agent's service reads, and set
   `ALERT_MANAGER_BACKEND` to the central host's `host:7754` and
   `ALERT_MANAGER_SOURCE_ID` to a name unique to this Suricata host.
3. Run the binary (e.g. under a systemd unit) pointed at the Suricata
   `alert.json` file via `ALERT_MANAGER_ALERT_FILE`.

## Recovery basics

- **Restart a service**: `docker compose restart <service>`. Alert,
  categorization, and audit data live in the `postgres_data` named volume and
  are unaffected by restarting or recreating the `backend`/`web` containers.
- **Back up the database**: `docker compose exec postgres pg_dump -U alertmanager alertmanager > backup.sql`.
- **Restore**: with the stack up, `cat backup.sql | docker compose exec -T postgres psql -U alertmanager alertmanager`.
- **Full data loss recovery**: recreate the stack with `docker compose up -d`,
  then restore the latest backup before running the bootstrap step again (the
  bootstrap is idempotent and safe to re-run).
