# SerpAPI Flight Data System — One-Page Overview

## Purpose
Cache-first flight search using SerpAPI (Google Flights), with full raw response preservation and structured storage for analytics.

## Core Components
- EnhancedFlightSearchClient (Main/enhanced_flight_search.py): cache-first search, week-range, structured ingest, CLI.
- SerpAPIFlightClient (Main/serpapi_client.py): validation, retry+jitter, rate limiting.
- Database Helper (DB/database_helper.py): WAL, checksum, drift detection, snapshot generation.

## Data Model (key tables)
- api_queries: raw API JSON, created_at timestamp (authoritative), never auto-pruned.
- flight_searches → flight_results → flight_segments (normalized), plus layovers, price_insights, route_analytics.
- schema_version (baseline 2025.09.08-baseline) and migration_history with checksum.

## Policies (must follow)
- Schema changes: strictly prohibited without owner double-confirmation; detect drift; keep snapshot in DB/current_schema.sql.
- Raw retention: ALL raw responses stored; not deleted by automatic cache cleanup. Prune only via explicit flags.
- Security: API keys only via environment variables; never logged or committed. Minimal, pinned dependencies with approval.
- Temp scripts: live only under tests/ (prefixed temp_/experimental_), remove or promote before finalize.

## Cache & Cleanup
- Structured cache freshness: 24h. Cleanup runs before searches; respects foreign keys and order.
- Raw api_queries untouched by automatic cleanup. Optional flags support explicit retention.

## Observability
- Structured JSONL events with taxonomy (api.*, efs.search.*, efs.cache.*), classic rotating logs.
- In-memory metrics (api_calls, api_failures, cache_hits/misses, retry_attempts, api_time_ms_total).

## CLI Examples (PowerShell)
- Single date: python Main/enhanced_flight_search.py LAX JFK 15-09-2025 22-09-2025 --adults 2
- Week range:  python Main/enhanced_flight_search.py LAX JFK 15-09-2025 --week

## Testing & Integrity
- Tests cover schema drift, FK integrity, cache behavior, week-range aggregation, metrics presence.
- WAL mode enabled; integrity and quick checks supported. Snapshot regeneration keeps schema in sync.

## WebApp (scope note)
- FastAPI layer adds `/api/flight_search` and auth UI wrapper around EFS (singleton). Debug endpoints removed post-stabilization.

## Next Enhancements (non-blocking)
- Metrics export (/metrics), JSONL rotation/compression, retry path tests, optional gzip for raw.

---
Aligned with README, SYSTEM_DOCUMENTATION, TECHNICAL_REFERENCE, DATA_CLEANUP_POLICY, and CHANGELOG (as of 2025-09-09).
 
