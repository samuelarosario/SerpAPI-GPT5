# SerpAPI Flight Data System

![Version](https://img.shields.io/badge/version-v0.3.0-blue.svg) ![Status](https://img.shields.io/badge/status-stable-success.svg)

Release v0.3.0: import path stabilization, metrics singleton guard, schema checksum + CLI JSON/force enhancements.
See CHANGELOG for details.

Badge automation: GitHub Actions will publish tests/coverage badges under this repository (SerpAPI-GPT5) once configured. Until then, dynamic badge links are intentionally omitted to avoid broken images.

CI consolidation: Workflows are merged into a single `ci.yml` running tests on Python 3.11, 3.12, 3.13. Coverage thresholds are enforced by failing the test job if coverage drops below target.

A comprehensive flight data collection, storage, and analysis system using SerpAPI Google Flights API.

## 📄 Reports

- Architecture & Core Components (2025-09-12):
    - HTML: [ARCHITECTURE_OVERVIEW_2025-09-12.html](./Reports/ARCHITECTURE_OVERVIEW_2025-09-12.html)
    - Markdown: [ARCHITECTURE_OVERVIEW_2025-09-12.md](./Reports/ARCHITECTURE_OVERVIEW_2025-09-12.md)
- Latest In-Depth Evaluation (2025-09-12):
    - HTML: [IN_DEPTH_EVALUATION_2025-09-12.html](./Reports/IN_DEPTH_EVALUATION_2025-09-12.html)
    - Markdown: [IN_DEPTH_EVALUATION_2025-09-12.md](./Reports/IN_DEPTH_EVALUATION_2025-09-12.md)
- Previous Evaluation (2025-09-11):
    - HTML: [Project-Evaluation-2025-09-11-HTML-Report.html](./Reports/Project-Evaluation-2025-09-11-HTML-Report.html)

## 🎯 System Overview

This system provides complete flight data management capabilities:
- **API Integration**: Search flights using SerpAPI Google Flights API
- **Data Storage**: Store ALL raw data and structured flight information
- **Analysis Tools**: Comprehensive flight data analysis and reporting
- **Real-time Processing**: Process and analyze flight searches immediately

## 📁 Project Structure

```
SerpAPI/
├── Main/                           # Main application code
│   ├── config.py                   # Configuration settings
│   ├── serpapi_client.py           # SerpAPI client implementation
│   ├── flight_processor.py         # (Legacy) older processing utilities (superseded by enhanced client)
│   ├── enhanced_flight_search.py   # Unified cache-first search + storage engine (CLI capable)
│   └── core/                       # Shared validation & logging utilities
├── DB/                             # Database files and scripts
│   ├── Main_DB.db                  # SQLite database
│   ├── database_helper.py          # DB utilities (WAL, checksum, drift detection, snapshot)
│   ├── current_schema.sql          # Auto-generated canonical schema snapshot
│   └── migrate_drop_query_timestamp.py  # Legacy one-off migration helper
├── tests/                          # Test suite (also hosts any temp_ experimental scripts)
├── agent-instructions.md           # Agent guidelines
└── requirements.txt                # Project requirements
```

## 🚀 Quick Start

### 1. Environment Setup (Persistent)

Use the bootstrap script to create a local venv and install all dependencies (root + WebApp). This makes new sessions reproducible even after re-cloning the folder.

```powershell
# From repo root
.\scripts\bootstrap.ps1            # create .venv and install deps
.\scripts\bootstrap.ps1 -RunServer  # also start the WebApp on http://127.0.0.1:8013
```

Alternatively, manual setup:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# (optional) .\.venv\Scripts\python.exe -m pip install -r WebApp\webapp_requirements.txt
```

### 2. Configuration

**Environment Variable (Secure):**
```bash
# Windows PowerShell
[System.Environment]::SetEnvironmentVariable("SERPAPI_KEY", "your_actual_key", [System.EnvironmentVariableTarget]::User)
```

**Security Note:** API keys are stored securely in environment variables only - never in plain text files.

Tip: you can also create a .env in repo root for the WebApp config loader (not committed):
```
SERPAPI_KEY=your_actual_key
WEBAPP_JWT_SECRET=change_me_dev_secret_change_me
```

### 3. Database Setup

**⚠️ IMPORTANT: Schema modifications are STRICTLY PROHIBITED without explicit owner approval ⚠️**

The database is already initialized with an optimized schema. To verify:
```bash
cd DB  
python DB/migrate_drop_query_timestamp.py  # Only if upgrading a pre-enhanced legacy DB
```

Current schema is documented in `DB/current_schema.sql` (auto-generated). Regenerate via `SerpAPIDatabase.generate_schema_snapshot()` after any approved structural migration.

### 4. Test the System

**Run a sample search (real API key required):**
```powershell
python Main/enhanced_flight_search.py LAX JFK 15-09-2025 22-09-2025 --adults 2
```

**Week range example:**
```powershell
python Main/enhanced_flight_search.py LAX JFK 15-09-2025 --week
```

### 5. (Optional) Session Cleanup Automation

Use the provided script to prune expired cached structured search data while preserving raw API data (raw retained by default):

```powershell
python Main/session_cleanup.py --cache-age-hours 24 --orphans --vacuum --json
```

Force pruning of raw API rows aligned to the same cache-age cutoff (advanced / irreversible):

```powershell
python Main/session_cleanup.py --cache-age-hours 24 --prune-raw-cache-age --json
```

Target raw retention independent of cache-age (e.g. keep only last 30 days raw):

```powershell
python Main/session_cleanup.py --raw-retention-days 30 --json
```

Raw data (api_queries) is NEVER deleted by automatic cache maintenance; only removed when you explicitly set a retention:

```powershell
# Keep only last 7 days of raw queries (irreversible)
python Main/session_cleanup.py --raw-retention-days 7
```

Or prune raw in the same pass as structured cache window:

```powershell
python Main/session_cleanup.py --cache-age-hours 12 --prune-raw-cache-age
```

To run automatically when closing a dev session you can create a VS Code task and invoke it manually before exit, or add a PowerShell profile snippet:

```powershell
function Close-SerpApiSession {
    Push-Location "C:\Users\MY PC\SerpAPI - V3"
    python Main/session_cleanup.py --cache-age-hours 24 --orphans
    Pop-Location
}
```

Then call `Close-SerpApiSession` before closing the terminal.

## 🔧 Core Components

### 1. SerpAPI Client (`serpapi_client.py`)

Features:
- ✅ Complete SerpAPI Google Flights integration
- ✅ Parameter validation and error handling
- ✅ Rate limiting and retry logic
- ✅ Support for round-trip, one-way, and multi-city searches

**Usage Example:**
```python
from serpapi_client import SerpAPIFlightClient

client = SerpAPIFlightClient()

# Search round-trip flights
result = client.search_round_trip(
    departure_id='LAX',
    arrival_id='JFK',
    outbound_date='2025-09-15',
    return_date='2025-09-22',
    adults=2
)
```

### 2. Enhanced Flight Search (Unified Engine)

Core runtime flight search functionality is now provided by `Main/enhanced_flight_search.py` (EnhancedFlightSearchClient) which supersedes older standalone scripts (removed). It provides:
- Cache-first (24h) lookups
- Raw API response persistence prior to structured parsing
- Structured multi-table ingestion (searches, results, segments, layovers, price insights)
- Week-range (7-day) search aggregation & price trend analysis
- Result type normalization and deterministic cache keying

Example:
```python
from Main.enhanced_flight_search import EnhancedFlightSearchClient

efs = EnhancedFlightSearchClient()
res = efs.search_flights('LAX','JFK','2025-09-15','2025-09-22')
if res.get('success'):
    print('Flights:', len(res.get('data', {}).get('best_flights', [])))
```

## 🌐 WebApp Flight Search UI (Overview)
- Authenticated at `/flight-search`.
- Form fields: Origin, Destination, Outbound date, optional Return date.
- Results are split into Outbound and Inbound tabs with counts; sorting and pagination are applied per tab.
- Headline displays the route, outbound and return dates (when provided), travel class, and trip mode (1-way / 2-way).

Backend behavior highlights:
- Airport auto-extract during structured storage ensures all segments and layovers persist even if some airports weren’t pre-seeded.
- Inbound fallback: if a round-trip response lacks inbound legs, a one‑way inbound fetch is performed and merged before storing, preventing missing return segments.
```

### 3. Data Processor (`flight_processor.py`)

Features:
- ✅ Processes complete SerpAPI responses
- ✅ Stores raw JSON data (requirement compliance)
- ✅ Extracts structured flight information
- ✅ Maintains data integrity and relationships

**Processing Flow:**
1. Store raw API response (preserves ALL data)
2. Extract flight search parameters
3. Process individual flight results and segments
4. Extract airport and airline information
5. Store price insights and analytics

### 4. Enhanced Flight Search CLI

You can invoke the unified engine directly from the terminal:
```powershell
python Main/enhanced_flight_search.py MNL POM 30-11-2025
python Main/enhanced_flight_search.py MNL POM 30-11-2025 07-12-2025 --adults 2 --travel-class 3
python Main/enhanced_flight_search.py MNL POM 30-11 --week --include-airlines PX --max-price 800
```

Primary date preference: DD-MM-YYYY (or DD-MM). Ambiguous (both parts <=12) interpreted as DD-MM.
Use `--help` or provide incomplete arguments to display the embedded helper.

## 🗄️ Database Schema

### Core Tables

1. **`api_queries`** - Raw API response storage (preserves ALL data)
2. **`flight_searches`** - Search parameters and metadata
3. **`flight_results`** - Individual flight options
4. **`flight_segments`** - Flight legs and details
5. **`layovers`** - Connection information
6. **`airports`** - Airport reference data
7. **`airlines`** - Airline reference data
8. **`price_insights`** - Price analysis data
9. **`route_analytics`** - Route performance metrics
10. **`schema_version`** - Single-row manifest capturing current schema baseline (`2025.09.08-baseline`)

### Key Features

- **Complete Data Preservation**: ALL raw API responses stored
- **Structured Access**: Optimized tables for analysis
- **Referential Integrity**: Proper relationships between entities
- **Performance Indexes**: Fast querying capabilities

## 📊 API Parameters Supported

### Search Parameters
- `departure_id` / `arrival_id` - Airport codes (IATA)
- `outbound_date` / `return_date` - Travel dates
- `adults` / `children` / `infants_in_seat` / `infants_on_lap` - Passengers
- `travel_class` - Economy, Premium, Business, First
- `currency` - Price currency (USD, EUR, etc.)
- `stops` - Number of stops filtering
- `max_price` - Maximum price filtering
- `deep_search` - Enhanced accuracy mode

### Advanced Filters
- `include_airlines` / `exclude_airlines` - Airline filtering
- `outbound_times` / `return_times` - Time range filtering
- `max_duration` - Maximum flight duration
- `emissions` - Low emissions filtering

## 📈 Analysis Features

### 1. Search Analytics
- Search volume by route
- Popular destinations
- Seasonal trends
- User behavior patterns

### 2. Price Analysis
- Route price trends
- Airline price comparison
- Price distribution analysis
- Historical price tracking

### 3. Performance Metrics
- Airline reliability
- Route efficiency
- Duration analysis
- Carbon footprint tracking

## 🔒 Data Requirements Compliance

✅ **ALL raw data from EVERY API query saved to local database**
✅ **No mock data - real API responses only**
✅ **Complete data persistence maintained**
✅ **Structured organization in designated directories**
✅ **Database schema confirmed before implementation**

## 📝 Usage Examples

### Basic Flight Search (Programmatic)
```python
from Main.enhanced_flight_search import EnhancedFlightSearchClient

client = EnhancedFlightSearchClient()
result = client.search_flights('LAX','JFK','2025-09-15','2025-09-22')
print(result.get('source'), result.get('success'))
```

### Week Range Search (Programmatic)
```python
from Main.enhanced_flight_search import EnhancedFlightSearchClient

client = EnhancedFlightSearchClient()
res = client.search_week_range('LAX','JFK','2025-11-30')
print(res.get('week_summary'))
```

## 🧪 Testing

### Testing
Temporary or experimental test scripts must reside in `tests/` and be prefixed with `temp_`.

Component checks (from project root):
```powershell
python Main/config.py          # Config sanity
python Main/serpapi_client.py  # Basic client invocation (will exit if no key)
python -m pytest -q            # Run automated test suite
```

## 🧬 Schema Versioning & Integrity

The system maintains a single-row `schema_version` table as a manifest.

- Current baseline: `2025.09.08-baseline`
- Initialization: created automatically on first connection if absent
- Purpose: anchor point for future incremental migrations beyond the legacy `query_timestamp` removal
- Policy: Any structural change (add/alter/drop table/column) MUST increment the version string (date + short tag) and be accompanied by:
    1. Migration function or script
    2. CHANGELOG entry
    3. Test coverage validating post-migration state

Implemented migration history (baseline row) with checksum backfill. Drift detection provided by `detect_schema_drift()` and checksum comparison. Snapshot regeneration keeps `current_schema.sql` synchronized.

## �‍💻 Development & Testing Workflow

Fast iteration guidelines:

1. Set environment variable once (PowerShell):
```powershell
[System.Environment]::SetEnvironmentVariable('SERPAPI_KEY','<key>',[System.EnvironmentVariableTarget]::User)
```
2. Run targeted tests while editing:
```powershell
python -m pytest tests/test_week_range_and_rate_limiter.py::test_week_range_aggregation -q
```
3. Inspect cache stats quickly:
```powershell
python Main/enhanced_flight_search.py LAX JFK 15-09 --stats
```
4. Prune only structured cache (keep raw):
```powershell
python Main/session_cleanup.py --cache-age-hours 24 --orphans
```
5. Explicitly prune raw aligned to cache window (irreversible):
```powershell
python Main/session_cleanup.py --cache-age-hours 24 --prune-raw-cache-age
```

Notes:
- Raw api_queries retention is indefinite unless a pruning flag is passed.
- Foreign key enforcement is active (see test_foreign_key_integrity) safeguarding relational deletes.
- Retry backoff now uses jitter to reduce thundering herds; tune in `SERPAPI_CONFIG`.

## �🔄 Refactor Status

The earlier Phase 1 sandbox has been fully merged. Shared utilities now live in `Main/core/` and the temporary `Phase 1/` directory is deprecated (safe to delete). All references to validation, logging, and date parsing are centralized.

## 📅 Standardized Date Parsing

CLI Accepted input formats (priority):
1. DD-MM-YYYY
2. DD-MM
3. Legacy fallback MM-DD-YYYY / MM-DD if unambiguous

Internal logic uses canonical `YYYY-MM-DD`. Return date must be >= outbound date. Utilities: `parse_date`, `within_horizon`, `validate_and_order` in `date_utils.py`.

## 🛠️ Configuration

### Environment Variable
- `SERPAPI_KEY` - Your SerpAPI key (must be set; no file-based fallback)

### Configuration File
- `Main/config.py` - System configuration

### Database Configuration
- Path: `DB/Main_DB.db`
- Type: SQLite
- Version: 2.0 (Enhanced Schema)
 - Migration: Legacy `query_timestamp` column removed (run `python DB/migrate_drop_query_timestamp.py` once if upgrading an existing DB)

## 📋 Requirements

### System Requirements
- Python 3.7+
- SQLite3
- Internet connection (for API calls)

### Python Packages
Core dependencies are in `requirements.txt`. Standard library modules (json, datetime, sqlite3) are used directly; third-party minimized to reduce attack surface.

### SerpAPI Account
- Sign up at https://serpapi.com/
- Get API key from dashboard
- 100 free searches per month

## 🔍 Troubleshooting

### Common Issues

**1. API Key Errors**
```
Error: SerpAPI key not found
Solution: Set SERPAPI_KEY environment variable (no local key file supported)
```

**2. Database Errors**
```
Error: unable to open database file
Solution: Ensure script is run from project root or let enhanced_flight_search compute absolute path automatically.
```

**3. Import Errors**
```
Error: Module not found
Solution: Ensure you're running from correct directory (Main/ or DB/)
```

### Debug Mode
Enable detailed logging in `config.py`:
```python
LOGGING_CONFIG = {
    'level': 'DEBUG',
    # Optional override path (central logger defaults to Main/logs/flight_system.log)
    'file_path': 'Main/logs/debug.log'
}
```

## 📊 System Status

### Current Implementation Status
- ✅ Database Schema: Complete
- ✅ API Client: Complete  
- ✅ Unified Search Engine: Complete
- ✅ Legacy Demos: Removed
- ✅ Documentation: Complete

### Database Statistics
- Tables: 11 (including enhanced schema)
- Indexes: 15 (optimized for performance)
- Data Preservation: 100% (ALL raw responses stored)
- Referential Integrity: Maintained

### API Coverage
- Search Types: Round-trip, One-way, Multi-city
- Parameters: 25+ supported parameters
- Filters: Advanced filtering capabilities
- Error Handling: Comprehensive error management

## 🎯 Future Enhancements

### Planned Features
- [ ] Real-time price alerts
- [ ] Route recommendation engine
- [ ] Machine learning price prediction
- [ ] Export capabilities (CSV, JSON)
- [ ] Web dashboard interface
- [ ] Automated scheduling

### Performance Optimizations
- [ ] Database query optimization
- [ ] Caching layer implementation
- [ ] Parallel processing capabilities
- [ ] Enhanced error recovery

## 📞 Support

For system issues or questions:
1. Check troubleshooting section
2. Review `agent-instructions.md`
3. Run a minimal search via `enhanced_flight_search.py`
4. Verify configuration with `Main/config.py`

## 📄 License

This project follows the requirements specified in agent-instructions.md and requirements.txt.

---

**System Ready for Production Use** ✅

All requirements have been implemented and tested. The system provides complete flight data collection, storage, and analysis capabilities with full compliance to the specified requirements.
