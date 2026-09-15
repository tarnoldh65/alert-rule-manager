# Alert Rule Manager

This repository contains the planning and implementation structure for the Alert Rule Manager MVP.

## Status
The project is in the planning phase. The implementation roadmap is documented in [docs/PLAN.md](docs/PLAN.md).

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

## Local development

Start the central services with `docker compose up --build`. Create the first local administrator after PostgreSQL is ready by running the backend bootstrap module with `ALERT_MANAGER_DATABASE_URL`, `ALERT_MANAGER_ADMIN_USERNAME`, and `ALERT_MANAGER_ADMIN_PASSWORD` set. Suricata agents use `ALERT_MANAGER_ALERT_FILE`, `ALERT_MANAGER_BACKEND`, and `ALERT_MANAGER_SOURCE_ID`.

