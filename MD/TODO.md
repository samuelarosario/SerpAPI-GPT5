# Project ToDo / Deferred Enhancements

Status legend: [ ] Planned | [~] In Progress | [x] Done (leave item & add date when completed)

## 1. Security & Auth Hardening
- [ ] Rate limiting / brute force protection
  - Goal: Throttle repeated failed login attempts (e.g. token bucket per IP + username)
  - Acceptance: >5 failed attempts in 60s returns 429 with `retry_after` hint.
- [ ] Refresh token rotation & revocation list
  - Goal: Invalidate stolen refresh tokens after first use.
  - Acceptance: Using an already-rotated token returns 401; rotation tracked in DB (jti + expiry).
- [ ] Stronger password policy & validation
  - Goal: Enforce minimum length + character diversity; reject breached passwords (optional).
  - Acceptance: Registration rejects weak passwords with structured error list.
- [ ] Optional MFA (stretch)
  - Goal: TOTP-based second factor for admin accounts.
  - Acceptance: Admin login flow requires OTP when enabled.

## 2. Database & Migrations
- [ ] Formal migration framework (Alembic)
  - Goal: Replace ad‑hoc ALTER TABLE logic.
  - Acceptance: `alembic upgrade head` reproduces current schema from empty DB.
- [ ] Seed management via migration or fixture script
  - Goal: Centralize default admin/user creation.
  - Acceptance: Idempotent seed step with clear logging.

## 3. Admin & User Management UX
- [ ] Pagination & filtering for `/auth/users`
  - Goal: Prevent large payloads and improve search.
  - Acceptance: Supports `?q=`, `?page=`, `?page_size=`; returns metadata block.
- [ ] Admin in-browser log viewer (auth + system)
  - Goal: View recent auth events without shell access.
  - Acceptance: `/admin/logs` endpoint (JWT admin) returns last N lines JSONL parsed.
- [ ] Bulk operations (activate/deactivate multiple users)
  - Goal: Efficiency for account hygiene.
  - Acceptance: Endpoint accepts list of user IDs with action; returns summary.

## 4. Observability & Operations
- [ ] Distinct liveness vs readiness endpoints
  - Goal: Support container orchestration probes.
  - Acceptance: `/health/live` (process OK), `/health/ready` (DB + critical deps OK).
- [ ] Structured request logging middleware (correlation IDs)
  - Goal: Trace multi-endpoint flows.
  - Acceptance: Every log line includes `trace_id` propagated via header.
- [ ] Metrics export (Prometheus format)
  - Goal: Basic counters: requests_total, auth_failures_total, active_users.
  - Acceptance: `/metrics` returns plaintext exposition; guarded or configurable.
- [ ] Graceful shutdown & startup hooks
  - Goal: Ensure DB sessions closed and no in-flight requests cut.
  - Acceptance: SIGTERM leads to clean shutdown log line; zero unhandled exceptions.
- [ ] Live tail option in Start-WebApp script
  - Goal: Optional `-Tail` switch to stream uvicorn log.
  - Acceptance: When provided, script spawns background server + foreground tail.

## 5. Reliability & Resilience
- [ ] Exponential backoff / retry wrapper for external calls (if/when added)
  - Goal: Standardize resilience policy.
  - Acceptance: Decorator or helper with jitter; metrics on retries.
- [ ] Circuit breaker for repeated dependency failures (future external APIs)
  - Goal: Fail fast after threshold.
  - Acceptance: Open state returns cached/fallback response; metric exposed.

## 6. Code Quality & Internal Tooling
- [ ] Type coverage improvement
  - Goal: mypy (or pyright) clean run.
  - Acceptance: CI gate blocks on typing errors; config stored in repo.
- [ ] Pre-commit hooks (ruff, formatting, safety)
  - Goal: Standardized local quality checks.
  - Acceptance: `.pre-commit-config.yaml` with documented install steps.
- [ ] CI pipeline (lint + test)
  - Goal: Automated validation on push / PR.
  - Acceptance: Workflow badge + passing run on main branch.

## 7. Configuration & Deployment
- [ ] Environment-based settings layering
  - Goal: Separate dev/test/prod profiles.
  - Acceptance: `APP_ENV` selects config file or overrides.
- [ ] Containerization (Dockerfile + compose)
  - Goal: Reproducible runtime with pinned Python & system deps.
  - Acceptance: `docker compose up` serves app at configured port.
- [ ] Secrets management integration (future)
  - Goal: Remove plaintext secrets from env vars.
  - Acceptance: Placeholder support or vault integration stub.

## 8. Security Auditing & Compliance
- [ ] Dependency vulnerability scanning
  - Goal: Automated alerts on CVEs.
  - Acceptance: Weekly scan report or CI gate (pip-audit, safety).
- [ ] JWT signing key rotation procedure
  - Goal: Enable key rollover without downtime.
  - Acceptance: Dual-key validation window implemented.

## 9. Data Lifecycle & Privacy
- [ ] Auth log retention & rotation policy
  - Goal: Avoid unbounded log growth.
  - Acceptance: Configurable max size / age with archival or purge.
- [ ] PII minimization in logs
  - Goal: Ensure hashed/anonymized where feasible.
  - Acceptance: Review checklist & automated lint rule (optional).

## 10. Stretch / Nice-to-Have
- [ ] Dark mode toggle on UI
  - Goal: Improve UX.
  - Acceptance: Persistent preference stored client-side.
- [ ] Real-time admin updates via WebSocket (user status, logs)
  - Goal: Live monitoring.
  - Acceptance: Basic WS channel with auth & broadcast events.

---
Generated backlog (deferred at user request). Update this file as items begin or complete.

- [ ] Flight Search UI: Optional "All" tab combining outbound+inbound, or stacked split view.
