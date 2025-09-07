# Changelog

## 2025-09-08
- Removed legacy `flight_search.py` CLI script (superseded by `EnhancedFlightSearchClient`).
- Updated `agent-instructions.md` with dependency security policy and tests-only temp script policy.
- Removed obsolete TODO from `enhanced_flight_search.py` (cache/storage already modularized).
- Updated `README.md` (eliminated Temp directory references; added unified engine section; debug log path moved to `/logs`).
- Updated `SYSTEM_STATUS.md` to reflect `/tests` structure and enhanced engine addition.
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
