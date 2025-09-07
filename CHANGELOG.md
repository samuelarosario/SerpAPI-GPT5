# Changelog

## 2025-09-07
- Consolidated Phase 1 sandbox into main codebase (`Main/core/` for shared utilities).
- Removed duplicated validation and rate limiting logic.
- Standardized logging via `core.logging_setup`.
- Updated default `travel_class` from Economy (1) to Business (3).
- Cleaned documentation: removed Phase 1 in-progress section, added refactor status.
- Defensive fix in `enhanced_flight_search.get_cache_stats` for missing columns.
- Added unified tests path (7 tests passing).
- Pending: physical removal of residual `Phase 1/` directory artifacts (tool deletion not applied).
