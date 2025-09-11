# AI Guide
Guidance for automated agents modifying this repository.

## Core Invariants
- `search_id` unique per normalized result set; structured writer is idempotent for the same `search_id`.
- Airports & airlines must exist (or be minimally upserted) before inserting segments referencing them.
- All persistence writes should be atomic: writer commits only after full batch assembly.
- Week aggregation performs 7 sequential day searches; do not parallelize yet (rate limiting concerns).

## Safe Extension Points
- Add new services in `Main/services/` and export via `REGISTRY`.
- Add new analytics modules under `Main/services/` using pure functions first.
- Add new pydantic models inside `Main/models/` and re-export in `__init__.py`.

## Avoid During Phase 1
- Renaming DB columns (requires migration coordination).
- Deleting legacy shims (`_store_structured_data`) until scripts updated.

## Logging & Metrics
- Use constants from `Main/constants.py` for event names.
- Prefer structured logging helpers (`log_event`, `log_exception`).

## Adding a Service
1. Create file `Main/services/<name>.py`.
2. Implement class with clear public method(s).
3. Import & add to `REGISTRY` in `Main/services/__init__.py`.
4. Add minimal unit test in `tests/` without hitting network.

## Pydantic Models
- Use snake_case field names matching DB columns where practical.
- Keep parsing (API shape) separate from domain normalization.

## Testing Strategy
- Unit: pure logic & services (fast, no network).
- Integration: orchestrator with in-memory or temp DB copy.
- Snapshot: normalized search output shape.

## Performance Notes
- SQLite busy errors: add small randomized backoff (future task) rather than tight loops.
- Keep large batch inserts inside single transaction for atomicity.

## Future Reserved Names
- `pricing_analytics` service planned.
- `http_client` abstraction planned.

Generated 2025-09-11.
