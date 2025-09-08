# SerpAPI Flight Search System - Complete Documentation

## � IMPORTANT: Database Schema Modification Policy

**⚠️ CRITICAL RESTRICTION ⚠️**

Database schema changes are **STRICTLY PROHIBITED** unless explicitly double-confirmed by the project owner. 

### Schema Change Policy:
- ❌ **NO** unauthorized schema modifications
- ❌ **NO** table structure changes without approval  
- ❌ **NO** column additions/deletions without explicit consent
- ❌ **NO** index modifications without review
- ✅ **ONLY** data operations (INSERT, UPDATE, DELETE) are permitted

### If Schema Change Required:
1. **STOP** - Do not proceed with any schema changes
2. **DOCUMENT** - Clearly document the proposed change and justification
3. **REQUEST** - Explicitly request approval from project owner
4. **WAIT** - Wait for explicit double-confirmation before proceeding
5. **BACKUP** - Create full database backup before any changes
6. **TEST** - Thoroughly test changes in isolated environment first

### Current Schema Status:
- **Schema File**: `DB/current_schema.sql` (canonical reference)
- **Last Generated**: Auto-generated from production database
- **Tables**: 10 production tables with optimized foreign key relationships
- **Status**: Production-ready and stable

---

## �📋 Table of Contents
1. [System Architecture Overview](#system-architecture-overview)
2. [Core Components](#core-components)
3. [Function Flow Diagrams](#function-flow-diagrams)
4. [Database Schema](#database-schema)
5. [API Integration](#api-integration)
6. [Usage Examples](#usage-examples)
7. [Development Guide](#development-guide)

---

## 🏗️ System Architecture Overview

```mermaid
graph TB
    User[👤 User] --> UI[🖥️ User Interface]
    UI --> Cache[💾 Local Cache Check]
    Cache --> |Hit| Return[📤 Return Cached Data]
    Cache --> |Miss| API[🌐 SerpAPI Call]
    API --> Store[💾 Store Data]
    Store --> Process[⚙️ Process & Analyze]
    Process --> Return
    
    subgraph "Core System"
        Cache
        API
        Store
        Process
    end
    
    subgraph "Data Layer"
        DB[(🗄️ SQLite Database)]
        Files[📁 File Storage]
    end
    
    Store --> DB
    Store --> Files
```

---

## 🧩 Core Components (Current)

### Enhanced Flight Search Client
`Main/enhanced_flight_search.py` – Unified search, cache-first, week range support, structured storage.

### Flight Search Cache
`Main/cache.py` – Cache key generation, lookup, cleanup (24h TTL).

### Database Helper (Legacy Support)
`DB/database_helper.py` – Underlying DB utilities (some legacy functions retained for reference).

### SerpAPI Client
`Main/serpapi_client.py` – Secure SerpAPI integration.

### Deprecated (Removed) Components
`api_approval_system.py`, `simple_api_approval.py`, `approved_flight_search.py`, demo scripts, analyzer modules – removed; see `DOC_DRIFT_MATRIX.md`.

---

## 🔄 Function Flow Diagrams

### 1. Flight Search Flow (Main Process)

```mermaid
flowchart TD
    Start([🔍 User Initiates Flight Search]) --> Validate{✅ Validate Parameters}
    Validate --> |Invalid| ErrorReturn[❌ Return Validation Error]
    Validate --> |Valid| CheckCache[💾 Check Local Cache]
    
    CheckCache --> CacheHit{🎯 Cache Hit?}
    CacheHit --> |Yes| CacheAge{⏰ Data Fresh?}
    CacheAge --> |Yes| ReturnCache[📤 Return Cached Data]
    CacheAge --> |No| CleanCache[🧹 Clean Old Data]
    
    CacheHit --> |No| NeedAPI[🌐 Need API Call]
    CleanCache --> NeedAPI
    
    NeedAPI --> MakeAPI[📞 Make API Call]
    
    MakeAPI --> APISuccess{✅ API Success?}
    APISuccess --> |Yes| StoreData[💾 Store in Database]
    APISuccess --> |No| APIError[❌ Return API Error]
    
    StoreData --> ProcessData[⚙️ Process Flight Data]
    ProcessData --> ExtractIATA[🔤 Extract IATA Codes]
    ExtractIATA --> UpdateRef[📊 Update Reference Tables]
    UpdateRef --> ReturnSuccess[✅ Return Success with Data]
    
    ReturnCache --> End([📋 End])
    ReturnSuccess --> End
    ErrorReturn --> End
    APIError --> End
```

### 2. Database Cache Management Flow

```mermaid
flowchart TD
    Start([🔍 Cache Check Request]) --> GenerateKey[🔑 Generate Cache Key]
    GenerateKey --> HashParams[#️⃣ Hash Parameters]
    HashParams --> QueryDB[🗄️ Query Database]
    
    QueryDB --> RecordFound{📋 Record Found?}
    RecordFound --> |No| CacheMiss[❌ Cache Miss]
    RecordFound --> |Yes| CheckAge[⏰ Check Data Age]
    
    CheckAge --> DataFresh{🕐 Within 24 Hours?}
    DataFresh --> |No| DataStale[📅 Data Stale]
    DataFresh --> |Yes| CacheHit[✅ Cache Hit]
    
    CacheHit --> ExtractData[📤 Extract Cached Data]
    ExtractData --> ReturnCached[📋 Return Cached Result]
    
    CacheMiss --> ReturnMiss[❌ Return Cache Miss]
    DataStale --> CleanOld[🧹 Clean Old Records]
    CleanOld --> ReturnMiss
    
    ReturnCached --> End([📋 End])
    ReturnMiss --> End
```

### (Removed) API Approval Flow
The previous interactive approval & cost control layer has been deprecated. All searches now proceed directly after validation using cache-first logic.

### 4. Data Storage and Processing Flow

```mermaid
flowchart TD
    Start([📥 API Response Received]) --> ValidateResponse{✅ Valid Response?}
    ValidateResponse --> |No| ErrorLog[❌ Log Error]
    ValidateResponse --> |Yes| ParseJSON[📋 Parse JSON Data]
    
    ParseJSON --> ExtractFlights[✈️ Extract Flight Data]
    ExtractFlights --> ProcessSegments[🛫 Process Flight Segments]
    
    ProcessSegments --> ExtractAirports[🏢 Extract Airport Data]
    ExtractAirports --> ExtractAirlines[🏢 Extract Airline Data]
    ExtractAirlines --> ExtractIATA[🔤 Extract IATA Codes]
    
    ExtractIATA --> StoreReference[📊 Store Reference Data]
    StoreReference --> StoreFlights[✈️ Store Flight Data]
    StoreFlights --> StoreRaw[📁 Store Raw Response]
    
    StoreRaw --> UpdateIndexes[📇 Update Database Indexes]
    UpdateIndexes --> GenerateCacheKey[🔑 Generate Cache Key]
    GenerateCacheKey --> Success[✅ Storage Complete]
    
    ErrorLog --> End([📋 End])
    Success --> End
```

### 5. Airline IATA Code Extraction Flow

```mermaid
flowchart TD
    Start([🔤 Extract IATA Code]) --> GetFlightNumber[📋 Get Flight Number]
    GetFlightNumber --> ValidateFormat{✅ Valid Format?}
    
    ValidateFormat --> |No| DefaultCode[📝 Use Default Code]
    ValidateFormat --> |Yes| ApplyRegex[🔍 Apply Regex Pattern]
    
    ApplyRegex --> RegexMatch{🎯 Regex Match?}
    RegexMatch --> |No| DefaultCode
    RegexMatch --> |Yes| ExtractCode[🔤 Extract 2-3 Char Code]
    
    ExtractCode --> ValidateIATA{✅ Valid IATA Format?}
    ValidateIATA --> |No| DefaultCode
    ValidateIATA --> |Yes| ReturnCode[📤 Return IATA Code]
    
    DefaultCode --> ReturnDefault[📤 Return "Unknown"]
    
    ReturnCode --> End([📋 End])
    ReturnDefault --> End
```

---

## 🗄️ Database Schema

### Core Tables Structure

```mermaid
erDiagram
    AIRPORTS {
        TEXT airport_code PK
        TEXT airport_name
        TEXT city
        TEXT country
        TEXT country_code
        TEXT timezone
        TEXT image_url
        DATETIME first_seen
        DATETIME last_seen
    }
    
    AIRLINES {
        TEXT airline_code PK
        TEXT airline_name
        TEXT logo_url
        TEXT alliance
        DATETIME first_seen
        DATETIME last_seen
    }
    
    FLIGHT_SEARCHES {
        INTEGER id PK
        TEXT search_id UK
        TEXT search_timestamp
        TEXT departure_id FK
        TEXT arrival_id FK
        TEXT outbound_date
        TEXT return_date
        INTEGER flight_type
        INTEGER adults
        TEXT currency
        TEXT cache_key
        TEXT raw_parameters
    }
    
    FLIGHT_RESULTS {
        INTEGER id PK
        TEXT search_id FK
        TEXT flight_id
        INTEGER total_price
        TEXT currency
        INTEGER total_duration
        TEXT booking_url
        INTEGER carbon_emissions
    }
    
    FLIGHT_SEGMENTS {
        INTEGER id PK
        INTEGER flight_result_id FK
        TEXT departure_airport_code FK
        TEXT arrival_airport_code FK
        TEXT airline_code FK
        TEXT flight_number
        TEXT departure_time
        TEXT arrival_time
        INTEGER duration
        TEXT aircraft_type
    }
    
    API_QUERIES {
        INTEGER id PK
        TEXT query_timestamp
        TEXT query_parameters
        TEXT raw_response
        TEXT query_type
        INTEGER status_code
        TEXT search_term
    }
    
    AIRPORTS ||--o{ FLIGHT_SEGMENTS : "departure"
    AIRPORTS ||--o{ FLIGHT_SEGMENTS : "arrival"
    AIRLINES ||--o{ FLIGHT_SEGMENTS : "operates"
    FLIGHT_SEARCHES ||--o{ FLIGHT_RESULTS : "contains"
    FLIGHT_RESULTS ||--o{ FLIGHT_SEGMENTS : "composed_of"
    FLIGHT_SEARCHES ||--o{ API_QUERIES : "generates"
```

---

## 🌐 API Integration

### SerpAPI Client Function Map

```mermaid
flowchart LR
    Client[SerpAPIFlightClient] --> Search[search_flights]
    Client --> RoundTrip[search_round_trip]
    Client --> OneWay[search_one_way]
    Client --> MultiCity[search_multi_city]
    
    Search --> Validate[_validate_parameters]
    Search --> BuildURL[_build_search_url]
    Search --> MakeRequest[_make_request]
    Search --> ParseResponse[_parse_response]
    
    MakeRequest --> RateLimit[_apply_rate_limit]
    MakeRequest --> HandleErrors[_handle_api_errors]
    MakeRequest --> Retry[_retry_logic]
    
    ParseResponse --> ExtractFlights[_extract_flight_data]
    ParseResponse --> ExtractPrices[_extract_price_data]
    ParseResponse --> ExtractMetadata[_extract_metadata]
```

---

## 📚 Usage Examples

### Basic Flight Search
```python
from enhanced_flight_search import EnhancedFlightSearchClient

# Initialize client
client = EnhancedFlightSearchClient()

# Search flights (checks cache first)
result = client.search_flights(
    departure_id='POM',
    arrival_id='MNL',
    outbound_date='2025-09-26',
    return_date='2025-10-03',
    adults=1
)

if result['success']:
    print(f"Found {len(result['data']['flights'])} flights")
    print(f"Data source: {result['source']}")  # 'cache' or 'api'
else:
    print(f"Search failed: {result['error']}")
```

### Approval Required Search
```python
from approved_flight_search import ApprovalRequiredFlightSearchClient

# Initialize approval client
client = ApprovalRequiredFlightSearchClient()

# Request search with approval
result = client.search_flights_with_approval(
    departure_id='POM',
    arrival_id='MNL',
    outbound_date='2025-09-26',
    reason='Business travel planning'
)

if result.get('approval_required'):
    request_id = result['approval_request_id']
    print(f"Approval needed. Request ID: {request_id}")
    print(f"Estimated cost: ${result['estimated_cost']:.4f}")
    
    # User approves the request
    final_result = client.approve_and_execute(request_id)
    print(f"Search completed: {final_result['success']}")
```

### Database Analytics
```python
from database_helper import SerpAPIDatabase

# Initialize database
db = SerpAPIDatabase()

# Get statistics
stats = db.get_database_stats()
print(f"Total searches: {stats['total_records']}")

# Get recent searches
recent = db.get_api_responses(query_type='flights', limit=10)
for search in recent:
    params = search['query_parameters']
    print(f"{params.get('departure_id')} → {params.get('arrival_id')}")
```

---

## 👨‍💻 Development Guide

### Class Hierarchy

```mermaid
classDiagram
    class EnhancedFlightSearchClient {
        +api_client: SerpAPIFlightClient
        +cache: FlightSearchCache
        +validator: FlightSearchValidator
        +search_flights()
        +_validate_search_params()
        +_extract_airline_iata_code()
        +_store_airline_info()
        +_store_airport_info()
    }
    
    class ApprovalRequiredFlightSearchClient {
        +base_client: EnhancedFlightSearchClient
        +pending_requests: Dict
        +search_flights_with_approval()
        +approve_and_execute()
        +reject_request()
        +get_pending_requests()
    }
    
    class SerpAPIFlightClient {
        +api_key: str
        +rate_limiter: RateLimiter
        +search_round_trip()
        +search_one_way()
        +_make_request()
        +_validate_parameters()
    }
    
    class FlightSearchCache {
        +db_helper: SerpAPIDatabase
        +search_cache()
        +store_flight_data()
        +cleanup_old_data()
        +_generate_cache_key()
    }
    
    class APICallMonitor {
        +calls_today: List
        +cost_estimates: Dict
        +log_api_call()
        +request_approval()
        +generate_usage_report()
    }
    
    class SerpAPIDatabase {
        +db_path: str
        +get_connection()
        +insert_api_response()
        +get_api_responses()
        +get_database_stats()
    }
    
    EnhancedFlightSearchClient --> SerpAPIFlightClient
    EnhancedFlightSearchClient --> FlightSearchCache
    ApprovalRequiredFlightSearchClient --> EnhancedFlightSearchClient
    FlightSearchCache --> SerpAPIDatabase
    APICallMonitor --> SerpAPIDatabase
```

### Key Design Patterns

1. **Cache-First Strategy**: Always check local database before API calls
2. **Approval Workflow**: Mandatory approval for API calls to manage costs
3. **Data Normalization**: Foreign key relationships to eliminate redundancy
4. **IATA Code Extraction**: Regex-based extraction from flight numbers
5. **Error Handling**: Comprehensive error capture and graceful degradation

### Performance Optimizations

1. **Database Indexes**: Optimized for common query patterns
2. **Cache Keys**: SHA-256 hashing for fast lookups
3. **Data Cleanup**: Automatic removal of stale data (>24 hours)
4. **Batch Operations**: Efficient bulk data insertion
5. **Connection Pooling**: Reuse database connections

---

## 🔧 Configuration

### Environment Setup
```powershell
# Set API key (Windows PowerShell - persists for current user)
[System.Environment]::SetEnvironmentVariable("SERPAPI_KEY", "your_key", "User")

# Or create a .env file at project root (NOT committed) with:
# SERPAPI_KEY=your_key
# Plaintext standalone key files (e.g. Temp/api_key.txt) are deprecated and disallowed.
```

### Database Configuration
```python
# config.py
DATABASE_CONFIG = {
    'path': '../DB/Main_DB.db',
    'cache_duration_hours': 24,
    'cleanup_interval_hours': 6
}

SERPAPI_CONFIG = {
    'base_url': 'https://serpapi.com/search',
    'timeout': 30,
    'max_retries': 3
}
```

---

## 🚀 Getting Started

1. **Clone/Setup**: Navigate to project directory
2. **Dependencies**: `pip install -r requirements.txt`
3. **API Key**: Set SERPAPI_KEY environment variable
4. **Database**: Run `python DB/schema_upgrade.py`
5. **Test**: Run `python Main/flight_system_demo.py`

---

*This documentation covers all major components and functions in the SerpAPI Flight Search System. Each flowchart represents the actual logic flow implemented in the codebase.*
