# Alert Rule Manager Plan

## Objective
Create an MVP system that ingests Suricata JSON alerts into PostgreSQL, presents them in a web UI, supports user-based categorization, tracks audit data, and produces operational reports. The project must be simple, deployable on Ubuntu, and designed for a Docker-based backend with the Rust forwarder running on the Suricata host.

## Confirmed architecture decisions

- Each Suricata instance runs on a separate standalone Ubuntu host.
- Several Suricata hosts will send alerts to one central backend deployment.
- The backend and web UI run in containers on a separate backend host.
- PostgreSQL uses persistent connected storage in the backend deployment.
- The first authentication implementation uses local application accounts.
- The authentication boundary should allow a future OAuth provider without redesigning application roles and permissions.
- Each agent connection must identify its Suricata source so alerts can be traced to the originating host.

## Sample alert contract

The repository sample at `alert.json` is newline-delimited JSON (one JSON object per line), not a single JSON array. The ingestion pipeline must:

- Parse one event per line and preserve the original JSON payload.
- Require the event timestamp, event type, and nested alert signature fields needed for rule reporting.
- Accept optional fields such as `flow_id`, source/destination network data, VLAN, flow statistics, HTTP, QUIC, application protocol, and alert metadata.
- Preserve repeated events with the same signature as separate alert occurrences while allowing reports to group them by rule identity (`gid`, `signature_id`, and revision).
- Add the configured Suricata host identity during forwarding or ingestion.

## Phase 0: Repository setup and scaffolding

### Scope
- Create the repository structure for backend, frontend, Rust agent, database, and deployment files.
- Add a minimal .gitignore and a base README.
- Draft environment variable templates and Docker structure for a central backend host with separate backend and web UI containers.
- Add test framework conventions for unit testing and migration validation.

### Success criteria
- [x] Repository has a clear layout for app, agent, db, and docs.
- [x] .gitignore exists and ignores local runtime, build, and secret files.
- [x] A minimal README explains the project and setup flow.
- [ ] Environment template files are ready for database, app, and agent configuration.
- [x] Local backend test commands are defined; Rust test execution remains pending on an Ubuntu host with Cargo.
- [x] Deployment documentation distinguishes the central container host from each standalone Suricata host.

## Phase 1: Database design and schema

### Scope
- Design PostgreSQL schema for alerts, rules, categories, users, audit records, and auto-categorization rules.
- Add migration scripts and seed values for default categories.
- Define indexes for alert lookup, categorization review, and report queries.

### Success criteria
- [x] Alerts table stores raw alert payload and metadata.
- [x] Users table supports access and role tracking.
- [x] Categories table supports naming and description.
- [x] Alert categorization table records category, timestamp, and user.
- [x] Audit table records user activity and alert state changes.
- [x] Auto-categorization rules table stores rule logic and metadata.
- [ ] Database migrations are versioned and tested.

## Phase 2: Suricata agent/service in Rust

### Scope
- Build the Rust service for each standalone Ubuntu Suricata host that reads its local `alert.json` output or equivalent log stream.
- Parse Suricata JSON records and normalize them for storage.
- Forward records from multiple agents to the central backend over TCP port 7754.
- Include a configured source/agent identity with every forwarded event.
- Add retry and basic error handling for dropped or malformed events.

### Success criteria
- [ ] Service compiles on Ubuntu with a clean Rust build.
- [x] Agent reads and parses Suricata alerts successfully in unit-test code.
- [x] JSON payloads are transformed into the expected backend envelope.
- [ ] Connection to backend over tcp/7754 is stable under normal conditions.
- [x] Events from multiple agents remain attributable to their originating Suricata host in the protocol design.
- [x] Unit tests cover parsing and serialization; failure/retry tests remain pending.
- [ ] Failed events are logged without crashing the service.

## Phase 3: Backend API and ingestion pipeline

### Scope
- Build the backend service in its own Docker container on the central backend host.
- Accept incoming TCP data from the Rust agent.
- Validate and insert alert data into PostgreSQL.
- Expose API endpoints for listing alerts, retrieving details, and updating categorization state.

### Success criteria
- [x] Backend accepts records from the agent protocol.
- [x] Alert ingestion inserts normalized fields and the original payload.
- [x] API endpoints return paginated alert lists and alert detail payloads.
- [x] Alert state transitions are tracked and persisted.
- [x] Unit tests validate the ingestion parser; database integration tests remain pending.

## Phase 4: Web UI and user workflow

### Scope
- Build the web UI in its own container and serve it through Apache, with nginx optionally used as the front-end connector.
- Add local user authentication and access control, keeping the identity boundary replaceable for a future OAuth provider.
- Present a paginated list of uncategorized alerts.
- Show the alert detail panel when an alert is selected.
- Display user focus state for active alerts across multiple users.

### Success criteria
- [x] Users can sign in with local accounts and access protected API views.
- [x] Local authentication works without coupling application authorization to the future OAuth provider.
- [x] UI shows a scrollable alert list.
- [x] Clicking an alert loads its details in a detail pane.
- [ ] Categorized alerts disappear from the active queue.
- [x] Backend supports user focus state for active alerts.
- [ ] Frontend behavior is covered by integration or UI tests.

## Phase 5: Categorization, review, and audit features

### Scope
- Allow users to assign a category to an alert.
- Record category timestamp and user.
- Create categorization definitions and admin controls.
- Add auto-categorization management from the configuration page.
- Track user actions for audit reporting.

### Success criteria
- [ ] Alerts can be categorized by authorized users.
- [ ] Every categorization stores the date and user who performed it.
- [ ] The configuration page supports user management and category creation.
- [ ] Auto-categorization controls can be created and maintained.
- [ ] Audit trails show changes by user and time.
- [ ] Unit tests validate categorization and audit logic.

## Phase 6: Reports and operational review

### Scope
- Produce reports for rules with more than one categorization.
- Show counts per categorization.
- List auto-categorized rules and their details.
- Provide summary data for operational review.

### Success criteria
- [ ] Report for multi-categorized rules is generated from stored data.
- [ ] Rules are grouped under each categorization.
- [ ] Auto-categorized rules are listed with their details.
- [ ] Reports are exportable or visible in the UI as required.
- [ ] Report queries are tested with realistic alert data.

## Phase 7: Deployment, persistence, and hardening

### Scope
- Containerize the database backend and application services.
- Use connected storage for PostgreSQL persistence.
- Verify the central Docker-based deployment on Ubuntu and the standalone Ubuntu agent installation on Suricata hosts.
- Add health checks, log rotation, and basic production hardening.

### Success criteria
- [ ] Docker stack starts successfully on Ubuntu systems.
- [ ] Persistent storage keeps data across restarts.
- [ ] Multiple standalone Suricata agents can connect to the central backend concurrently.
- [ ] Backend and agent services are monitored via health checks.
- [ ] Documentation covers deployment and recovery basics.
- [ ] High-risk paths such as ingestion and category updates are tested.

## Definition of done
The MVP is complete when all phases above reach their success criteria, the project is documented clearly, and the database, Rust agent, backend, and web UI work together in a reproducible Ubuntu/Docker setup with unit and integration tests covering the critical flows.

## Implementation notes
- Keep the design intentionally simple and avoid unnecessary abstractions.
- Prefer proven libraries and current stable versions.
- Use PostgreSQL as the canonical data store for alerts, classification, and user activity.
- Keep the agent lightweight and resilient to malformed input.
- Treat the web UI and config pages as admin and analyst tooling, not a general-purpose CMS.
- Treat `alert.json` as newline-delimited JSON and retain unknown event fields in the raw payload.
- Keep source identity separate from user identity; Suricata hosts are ingestion clients, not application users.

## Verification gate
The plan was approved for execution on 2026-09-14. Remaining unchecked criteria are explicitly tracked below and must be completed before production use.

## Remaining execution prerequisites

The architecture and sample input are now defined. Before implementation begins, confirm these operational values:

- [ ] Central backend hostname/IP and the network ranges allowed to connect on tcp/7754.
- [ ] Whether tcp/7754 must use TLS and how each Suricata agent will authenticate to the backend.
- [ ] The initial local account roles and the first administrator bootstrap procedure.
- [ ] Whether an alert may receive multiple categories or exactly one final category.
- [ ] Report output format for the MVP (web UI only, CSV, or another format).
- [ ] Alert and audit-log retention period.

## Execution verification

- Backend tests: passed, 3 tests.
- Backend Python compilation: passed.
- Web production build: passed.
- Docker Compose configuration validation: passed.
- Docker runtime smoke test: not completed because Docker became unavailable in the terminal environment after configuration/build validation.
- Rust agent tests: not completed because Cargo is not installed on the Windows development host; run `cargo test --manifest-path agent/Cargo.toml` on Ubuntu before deployment.
