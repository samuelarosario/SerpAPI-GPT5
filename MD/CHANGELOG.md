# Changelog

## 2025-09-08
### Observability & Metrics Enhancements
- Added in-memory metrics counters (api_calls, api_failures, cache_hits, cache_misses, retry_attempts, api_time_ms_total) with snapshot via `EnhancedFlightSearchClient.get_cache_stats()`.
- Introduced structured JSON logging module (`core/structured_logging.py`) writing to `logs/flight_events.jsonl`.
- Instrumented `serpapi_client` and `enhanced_flight_search` with lifecycle events: `search.start/success/error`, `api.attempt/success/retry/failed/exception`, cache hit/miss, raw & structured storage success/error, week range per-day events, completion summary.
- Replaced deprecated `datetime.utcnow()` with timezone-aware `datetime.now(datetime.UTC)` for event timestamps.
- Added metrics test (`tests/test_metrics.py`); total tests increased to 20 (all passing).

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
