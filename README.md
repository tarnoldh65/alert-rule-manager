# Alert Rule Manager

This repository contains the planning and implementation structure for the Alert Rule Manager MVP.

## Status
Core ingestion, categorization, auto-categorization, reporting, and the web UI are implemented and covered by unit tests; see [docs/PLAN.md](docs/PLAN.md) for the phase-by-phase checklist and open items.

## Scope
The system will ingest Suricata alerts in JSON form, store them in PostgreSQL, provide a web UI for review and categorization, support user accounts and audit tracking, and generate summary reports.

## Planned stack
- PostgreSQL for persistent alert, categorization, and audit data
- Apache as the web service layer
- nginx as an optional connector/proxy layer
- Rust agent on the Suricata host for forwarding alerts to the backend
- Ubuntu hosts for all systems
- Docker-based backend deployment with persistent storage

## Project documents
- [AGENTS.md](AGENTS.md)
- [docs/PLAN.md](docs/PLAN.md)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

## Local development

Copy `.env.example` to `.env` (and `backend/.env.example`, `agent/.env.example` for those components), then start the central services with `docker compose up --build`. Create the first local administrator after PostgreSQL is ready by running `docker compose exec backend python -m app.bootstrap`. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for host setup and recovery steps.

