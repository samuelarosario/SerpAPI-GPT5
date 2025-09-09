# SerpAPI-GPT5 - System Functionality Report

## Overview
Cache-first flight search built on SerpAPI (Google Flights). Raw API responses are preserved; structured results are normalized into SQLite for fast reuse, analysis, and UI/API access.

## Core Components
- Main/enhanced_flight_search.py: EnhancedFlightSearchClient (CLI + library). Validates params -> cache lookup -> optional SerpAPI call with retry -> store raw + structured.
- Main/cache.py: Cache keying, lookup, and TTL-based cleanup (24h freshness for structured cache).
- DB/database_helper.py: Connection bootstrap, schema version/baseline, checksums, integrity utilities.
- Main/session_cleanup.py: Safe, on-demand cleanup tool (structured TTL purging, optional raw retention pruning).
- WebApp (FastAPI, documented): Authenticated UI + /api/flight_search thin wrapper over EFS client.

## Data Model (SQLite)
- api_queries: Raw JSON responses + metadata (retained by default).
- flight_searches: One row per search (route, dates, params, cache_key, created_at).
- flight_results, flight_segments, layovers: Normalized results per search.
- price_insights, route_analytics, airlines, airports, migration_history, schema_version.

## Cache & Expiration
- TTL: 24 hours for structured cache (configurable per call).
- Lookup: search_cache() returns a hit only if flight_searches.created_at > now - TTL and matches cache_key.
- Expiry effect: Stale rows are ignored (treated as cache misses).

## Purging (Structured Cache)
- Automatic (throttled): Each EFS search call triggers cleanup_old_data() at most once every 15 minutes, deleting expired flight_searches and dependents (flight_results, flight_segments, layovers, price_insights). Raw data is not touched.
- Manual: Main/session_cleanup.py supports:
  - --cache-age-hours N (structured TTL purge)
  - --raw-retention-days D or --prune-raw-cache-age (raw pruning, opt-in)
  - --vacuum, --orphans, --dry-run, --json

## Raw Data Retention (Default-Safe)
- Raw api_queries rows are never removed by cache maintenance.
- Pruning raw requires explicit flags (or retention env) via session_cleanup.py.

## Interfaces
- CLI examples:
  - Single-date: python Main/enhanced_flight_search.py LAX JFK 15-09-2025 22-09-2025 --adults 2
  - Week range:  python Main/enhanced_flight_search.py LAX JFK 15-09-2025 --week
- Web API (documented): /api/flight_search -> calls EFS client; UI renders normalized results.

## Observability
- Structured JSONL + classic logs (events: api.*, efs.search.*, efs.cache.*).
- In-memory metrics: api_calls, api_failures, cache_hits, cache_misses, retry_attempts, api_time_ms_total (exposed via EFS client helper).

## Quality & CI
- Tests cover schema drift, checksum/snapshot, FK integrity, cache behavior, week-range aggregation, metrics presence, CLI date parsing.
- CI workflows: linting (ruff), security (pip-audit), tests/coverage, optional badge updates.

## Operational Notes
- Time semantics: flight_searches.created_at stored as ISO string; expiration math assumes UTC at read-time. TTL comparisons are consistent in practice.
- DB safety: Foreign keys enforced; idempotent upserts for airports/airlines; WAL mode enabled where supported.

## Quick Maintenance
- Inspect/clean structured cache: python Main/session_cleanup.py --cache-age-hours 24 --orphans --json
- (Optional) Align raw to cache window: add --prune-raw-cache-age (irreversible, opt-in).

---
Status: Cache-first flow is live; raw retention is safe by default; structured cache TTL is enforced on read and purged on a 15-minute throttle or via the cleanup utility.
