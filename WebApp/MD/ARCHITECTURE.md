# WebApp Architecture (Initial Draft)

## Scope
This document tracks the evolving architecture of the Flight WebApp layer. The initial milestone focuses on **user authentication**.

## guiding principles
- Security first: least privilege, hashed secrets, short-lived tokens.
- Separation: Keep auth logic modular (`auth/` package) for reuse.
- Observability: Reuse structured logging + metrics pattern.
- Extensibility: Future UI (React/Svelte) or mobile clients consume same API.

## high-level components (planned)
- `main.py` FastAPI entrypoint
- `core/config.py` (webapp-specific settings; may read from root env vars)
- `auth/models.py` SQLAlchemy models (`User`)
- `auth/schemas.py` Pydantic request/response models
- `auth/hash.py` password hashing utilities (argon2 preferred)
- `auth/jwt.py` token creation & validation
- `auth/routes.py` login & register endpoints
- `db/session.py` DB engine & session factory (SQLite initially)

## data model (initial)
User
- id (int, PK)
- email (unique, indexed)
- password_hash
- is_active (bool)
- created_at (utc)
- updated_at (utc)

## authentication flow (jwt)
1. User registers (email + password)
2. Password hashed (argon2id)
3. User stored
4. Login with email/password
5. Verify hash -> issue access (15m) & refresh (7d)
6. Refresh endpoint exchanges refresh for new access

## security choices
- Hashing: `argon2-cffi` (memory-hard). If install issues, fallback to bcrypt.
- Tokens: `python-jose` with HS256, secret from environment `WEBAPP_JWT_SECRET` (>=32 chars recommended).
- Token invalidation strategy (future): rotate refresh token version stored on user record.

## next iterations
- Add roles/permissions (RBAC)
- Integrate with flight search engine (authorized search requests)
- Rate limiting per user
- OAuth social login (optional)

