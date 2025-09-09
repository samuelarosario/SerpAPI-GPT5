# SerpAPI Flight WebApp (Bootstrap)

This directory will contain the upcoming web application layer for the flight data system.

## Goals
- Provide a secure user-facing interface.
- Start with authentication & session management (minimal UI placeholder).
- Integrate later with existing flight search core modules.

## Current Status
Running: Auth, user bootstrap, JWT-based /auth endpoints, and a minimal UI with a working `/api/flight_search` proxy into the EnhancedFlightSearch client.

## Planned Stack (Subject to refinement)
- Framework: FastAPI (async, modern, OpenAPI generation).
- Auth: `python-jose` for JWT signing + `passlib[bcrypt]` for password hashing.
- DB: Reuse existing SQLite (`DB/Main_DB.db`) via SQLAlchemy session layer (to be added) OR dedicated auth tables.
- Session Strategy: Stateless JWT access token + optional refresh token endpoint.
- CSRF: Not applicable for pure API (will require if browser forms introduced).
- Rate Limiting: Reuse in-memory limiter or implement Redis if multi-process scaling.

## Security Baseline
- Argon2 or bcrypt for password hashing (preferring Argon2 if package acceptable; fallback bcrypt).
- JWT short-lived access tokens (15m) + refresh tokens (7d) stored HttpOnly (future web UI) or returned via API.
- Strict dependency pinning.
- Linting & static analysis inherited from root (`ruff`, `mypy`).

## Next Steps
1. Add `pyproject.toml` extras or separate `webapp_requirements.txt` (decide consolidation strategy).
2. Implement minimal FastAPI app with health endpoint.
3. Add user model + migration (auth_users table) and password hashing helper.
4. Implement registration & login endpoints (issue JWT).
5. Write tests under `tests/webapp/` for auth flows.

## How to run (Windows PowerShell)

```powershell
# From repo root
.\scripts\bootstrap.ps1 -RunServer

# Then visit:
# http://127.0.0.1:8013/
# Demo users are auto-created:
#   user@local / user
#   admin@local / admin
```

