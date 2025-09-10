# Changelog

## 2025-09-10
### Web App Flight Search: Tabs, Return Date, Headline improvements
- Added optional Return date field to the Flight Search UI and API passthrough.
- Headline now shows route on separate lines with outbound and return dates, travel class, and trip mode (1-way/2-way), left-aligned for readability.
- Introduced Outbound and Inbound tabs to separate results by direction; each tab shows its own count and supports sorting and pagination.

### Backend Reliability: Airport auto-extract and Inbound fallback merge
- Structured storage now auto-extracts minimal airport stubs (code/name/city when available) for any airports referenced by segments or layovers. This ensures all segments persist even if the airport wasn’t pre-seeded in the curated table.
- Implemented inbound one‑way fallback: when the round-trip API response omits inbound legs for the specified return date, the system performs a one-way inbound search (arrival→departure) and merges those flights before structured storage. Prevents missing return segments going forward.
- Cache behavior unchanged: structured results are preferred; raw fallback is used only when no structured segments exist at all.
- No schema changes.

### Scripts & Tooling
- Added `scripts/seed_airlines.py` to seed airline reference data.
- Added `scripts/smoke_store_return_segments.py` to validate segment persistence for previously unknown airports.
- Added `scripts/backfill_inbound_segments.py` to repair historical searches where return segments were missing by merging inbound one‑way results and re-storing.

### Operations
- Server lifecycle controls tightened in dev (explicit port kill before start).
- Backfilled SYD→HND (2026-01-01 / 2026-01-10) case; inbound legs are now present and dated correctly.

## 2025-09-08
### Web App Flight Search Integration & UI Refinements
- Added authenticated web UI route `/flight-search` (form: origin, destination, date) and API endpoint `/api/flight_search` invoking `EnhancedFlightSearchClient` (cache-first then API) with minimal parameters.
- Implemented singleton initialization for `EnhancedFlightSearchClient` in `WebApp/app/main.py` to prevent duplicate imports, path divergence, and metrics duplication.
- Added resilient lazy import path adjustment (only once) to handle direct web app runs without prior PYTHONPATH configuration.
- Introduced temporary diagnostic endpoints (`/debug/flight_searches_summary`, `/debug/efs_env`, `/debug/efs_ping`) during persistence investigation; subsequently fully removed after stabilization.
- Enhanced structured storage reliability by ensuring pre-insert upserts for referenced airports/airlines (avoiding silent FK failures) and added post-commit verification logging (counts of inserted flight_results & segments) retained for observability.
- Updated flight search UI result rendering: replaced raw object placeholders (`[object Object]`) with formatted cards showing route (origin→destination), price (USD), total duration (hh h mm m), stop count, and per-segment rows (dep→arr, airline+flight, times, segment minutes).
- Commit references: `fa5422a` (logging & data write confirmation), `65885d2` (remove debug endpoints), `7fe41f0` (formatted flight search UI cards).
- No schema changes required; database writes confirmed via existing structured storage pipeline.
- Deferred (future): transform card grid into Google-style vertical result list with sorting & filtering (price, duration, stops), pagination/virtualization, and richer fare class display.

### Observability & Metrics Enhancements
- Added in-memory metrics counters (api_calls, api_failures, cache_hits, cache_misses, retry_attempts, api_time_ms_total) with snapshot via `EnhancedFlightSearchClient.get_cache_stats()`.
- Introduced structured JSON logging module (`core/structured_logging.py`) writing to `logs/flight_events.jsonl`.
- Instrumented `serpapi_client` and `enhanced_flight_search` with lifecycle events: `search.start/success/error`, `api.attempt/success/retry/failed/exception`, cache hit/miss, raw & structured storage success/error, week range per-day events, completion summary.
- Replaced deprecated `datetime.utcnow()` with timezone-aware `datetime.now(datetime.UTC)` for event timestamps.
- Added metrics test (`tests/test_metrics.py`); total tests increased to 20 (all passing).
### Import Path Stabilization (2025-09-08)
- Standardized all internal imports to use `from Main.config import ...` instead of relying on ambiguous `config` resolution.
- Added `Main/__init__.py` (namespace initializer) and minimal, centralized path bootstrap in runtime modules.
- Removed duplicate module loading that previously caused separate `METRICS` instances (e.g., `core.metrics` vs `Main.core.metrics`).
- Added `structured_storage_failures` counter and test (`test_structured_storage_failure_metric.py`).
 - Added guard & alias coalescing in `core/metrics.py` to fail fast on conflicting duplicate loads and unify module identity.


- Added automated schema migration (drop legacy query_timestamp) with safety & test coverage.
- Updated cache logging to include search_id context; unified jitter per spec.
- Extracted CLI date parsing function; added ambiguous date tests.
- Added foreign key integrity, migration, week range aggregation, CLI date parsing tests (total 19 tests).
- Updated documentation (TECHNICAL_REFERENCE, SYSTEM_DOCUMENTATION, FUNCTION_FLOWCHARTS, SYSTEM_STATUS) to remove legacy query_timestamp references.
- Added cache_key index creation on initialization for improved lookup performance.
- Replaced stdout prints in database helper with structured logging.
- Fixed stale LOGGING_CONFIG.file_path referencing removed Temp directory (now points to Main/logs/flight_system.log).
- Removed deprecated instruction to store API key in Temp/api_key.txt; standardized on environment variable or .env file.
- Removed legacy `flight_search.py` CLI script (superseded by `EnhancedFlightSearchClient`).
- Updated `agent-instructions.md` with dependency security policy and tests-only temp script policy.
- Removed obsolete TODO from `enhanced_flight_search.py` (cache/storage already modularized).
- Updated `README.md` (eliminated Temp directory references; added unified engine section; debug log path moved to `/logs`).
- Updated `SYSTEM_STATUS.md` to reflect `/tests` structure and enhanced engine addition.
- Added schema version manifest table (`schema_version`) with baseline `2025.09.08-baseline` auto-initialization and helper `get_schema_version()`.
- Added unit test `tests/test_schema_version.py`; total tests now 22 (all passing).
- Added structured storage refactor with `_store_structured_data` method; tests now 9 passing.
- Reinforced raw API persistence and api_query_id linkage in search workflow.
- Dependency policy: require double-confirm before adding new external packages; pin versions.

## 2025-09-07
- Consolidated Phase 1 sandbox into main codebase (`Main/core/` for shared utilities).
- Removed duplicated validation and rate limiting logic.
- Standardized logging via `core.logging_setup`.
- Updated default `travel_class` from Economy (1) to Business (3).
- Cleaned documentation: removed Phase 1 in-progress section, added refactor status.
- Defensive fix in `enhanced_flight_search.get_cache_stats` for missing columns.
- Added unified tests path (7 tests passing).
- Pending: physical removal of residual `Phase 1/` directory artifacts (tool deletion not applied).
