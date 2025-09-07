# Phase 1 Refactor Snapshot

This directory contains an isolated workspace for Phase 1 improvements:

Improvements implemented:

Pending (not yet merged back):

Next steps:
1. Adapt `serpapi_client.py` and `enhanced_flight_search.py` here to use shared validator & limiter.
2. Add price parsing before DB inserts.
3. Run smoke tests.
4. Re-evaluate and then merge into root project.

## Date Parsing & Validation (Standardized)

Accepted input formats now (legacy CLI & Phase 1 CLI):
- MM-DD-YYYY (e.g. 12-30-2025)
- MM-DD (rolls to next year if already past in current year; leap day searches forward up to 5 years)

All internal processing converts to canonical YYYY-MM-DD.

Return date ordering is validated (return >= outbound). Horizon checks use config min/max days unless `--no-horizon` (Phase 1 CLI) is supplied.

Shared utility: `date_utils.py` (functions: `parse_date`, `within_horizon`, `validate_and_order`).

## Tests

Added unit tests:
- `tests/test_date_utils.py` – parsing & rollover
- `tests/test_validation.py` – horizon & format basics

Run: `python -m unittest discover -v`
