# Documentation Drift Matrix

Purpose: Track discrepancies between documentation claims and actual codebase components (2025-09-08 audit).

| Component (Documented) | File Referenced | Exists Now | Status | Action |
|------------------------|-----------------|------------|--------|--------|
| Flight Analyzer        | Main/flight_analyzer.py | No | Deprecated | Remove references from docs |
| Demo System Script     | Main/flight_system_demo.py | No | Deprecated | Remove references |
| Simulation Demo        | Main/simulation_demo.py | No | Deprecated | Remove references |
| API Approval System    | Main/api_approval_system.py | No | Deprecated | Clarify deprecation |
| Simple Approval        | Main/simple_api_approval.py | No | Deprecated | Clarify deprecation |
| Approved Flight Search | Main/approved_flight_search.py | No | Deprecated | Clarify deprecation |
| Cache Migration Tool   | DB/cache_migration.py | No | Deprecated | Remove references if not planned |
| Legacy Analyzer Tests  | References to analyzer in README | No | Outdated | Updated (commit e670d7e) |
| Temp/api_key.txt       | Temp/api_key.txt | No | Removed | Updated README |
| Week Range Search      | EnhancedFlightSearchClient.search_week_range | Yes | Active | Ensure test coverage |

Next Steps:
1. Purge or update remaining doc files: SYSTEM_DOCUMENTATION.md, PYTHON_EVALUATION_REPORT.md, CLEANUP_PLAN_2.md, CLEANUP_SUMMARY_FINAL.md.
2. Insert explicit deprecation block in those docs or archive them under `MD/archive/`.
3. Add tests for week range and CLI date ambiguity.

Audit Timestamp: 2025-09-08
