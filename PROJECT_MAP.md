# Project Map

High-level domain layout for rapid orientation (generated Option C Phase1).

## Domains
- Search Orchestration: `Main/enhanced_flight_search.py` (façade; delegates to services).
- Services:
  - Inbound completion: `Main/services/inbound_merge.py`
  - Week aggregation: `Main/services/week_aggregator.py`
  - CLI date parsing: `Main/services/cli_date_parser.py`
- Persistence:
  - Structured writer: `Main/persistence/structured_writer.py`
  - Cache layer: `Main/cache.py`
- API Client: `Main/serpapi_client.py`
- Metrics & Logging: `Main/core/metrics.py`, `Main/core/structured_logging.py`
- Validation: `Main/core/common_validation.py`, `date_utils.py`
- Database helpers & migrations: `DB/database_helper.py`, `DB/migrate_*.py`, `DB/current_schema.sql`
- Scripts / Ops: `scripts/*.ps1`, ETL/migration scripts in `DB/` and operational scripts in `scripts/`.
- Web Application (FastAPI + React): `WebApp/` (API), `WebApp/react-frontend` (UI).

## Data Flow (Round Trip Search)
User -> EnhancedFlightSearchClient.search_flights -> Cache check -> SerpAPI client -> InboundMergeStrategy -> StructuredFlightWriter -> Cache read-back -> Response.

## Key IDs
- `search_id`: External correlation of a single flight search response.
- `api_query_id`: Row id in `api_queries` (raw JSON).

## Configuration
- API and processing: `Main/config.py` (SERPAPI_CONFIG, PROCESSING_CONFIG, RATE_LIMIT_CONFIG).

## Future Extraction Targets
- Pricing analytics (trend, volatility) -> `services/pricing_analytics.py`
- HTTP abstraction -> `infra/http_client.py`
- Repository layer -> `persistence/repositories/*.py`

## Model Layer (new)
- Pydantic base models in `Main/models/`.

## Constants & Registries
- Event & metric keys: `Main/constants.py`
- Service registry: `Main/services/__init__.py` (REGISTRY)

---
Generated: 2025-09-11
