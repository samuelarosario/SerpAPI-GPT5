# SerpAPI System - Visual Function Map

## 🗺️ Complete System Function Mapping with Visual Flowcharts

---

## 📊 System Overview Map

```mermaid
mindmap
  root((SerpAPI System))
    Search Engine
      Enhanced Flight Search Client
        search_flights()
        _validate_search_params()
        _extract_airline_iata_code()
        _store_airline_info()
        _store_airport_info()
        _calculate_cache_age()
    // Deprecated (Sept 2025): Approval Required Client (removed)
    API Integration
      SerpAPI Client
        search_round_trip()
        search_one_way()
        search_multi_city()
        _validate_parameters()
        _build_search_url()
        _make_request()
        _parse_response()
        _handle_api_errors()
      Rate Limiter
        check_rate_limit()
        wait_if_needed()
        _calculate_delay()
    Data Management
      Database Helper
        insert_api_response()
        get_api_responses()
        get_database_stats()
        _update_metadata()
      Flight Search Cache
        search_cache()
        store_flight_data()
        cleanup_old_data()
        _generate_cache_key()
  // Deprecated (Sept 2025): Approval System (APICallMonitor)
    Validation
      Flight Search Validator
        validate_airport_code()
        validate_date_format()
        validate_passenger_count()
        _check_date_logic()
```

---

## 🔍 Main Search Flow Functions

### Primary Search Function: `search_flights()`

```mermaid
graph TD
    A[search_flights] --> B[cleanup_old_data]
    A --> C[build_search_params]
    A --> D[auto_generate_return_date]
    A --> E[_validate_search_params]
    E --> F{Validation OK?}
    F -->|No| G[return validation_error]
    F -->|Yes| H[search_cache]
    H --> I{Cache Hit?}
    I -->|Yes| J[_calculate_cache_age]
    J --> K{Data Fresh?}
    K -->|Yes| L[return cached_result]
    K -->|No| M[API Call Required]
    I -->|No| M
    M --> N{force_api?}
    N -->|Yes| O[Direct API Call]
    N -->|No| P[Check API Client Available]
    P --> Q{API Client Ready?}
    Q -->|No| R[return no_api_error]
    Q -->|Yes| S{return_date exists?}
    S -->|Yes| T[search_round_trip]
    S -->|No| U[search_one_way]
    T --> V[API Success?]
    U --> V
    V -->|No| W[return api_error]
    V -->|Yes| X[store_flight_data]
    X --> Y[_store_airline_info]
    Y --> Z[_store_airport_info]
    Z --> AA[return success_with_data]
    
    style A fill:#e1f5fe
    style L fill:#c8e6c9
    style AA fill:#c8e6c9
    style G fill:#ffcdd2
    style W fill:#ffcdd2
    style R fill:#ffcdd2
```

### Cache Management Functions

```mermaid
graph TD
    A[search_cache] --> B[_normalize_parameters]
    B --> C[_generate_cache_key]
    C --> D[SHA256 Hash]
    D --> E[Calculate 24h cutoff]
    E --> F[Query Database]
    F --> G{Record Found?}
    G -->|No| H[return None - Cache Miss]
    G -->|Yes| I[Parse JSON Response]
    I --> J[Add Cache Metadata]
    J --> K[return Cached Data]
    
    L[store_flight_data] --> M[Generate Cache Key]
    M --> N[Store Search Record]
    N --> O[Process Each Flight]
    O --> P[Store Flight Results]
    P --> Q[Process Flight Segments]
    Q --> R[Extract Airlines/Airports]
    R --> S[Store Reference Data]
    S --> T[Store Raw API Response]
    
    U[cleanup_old_data] --> V[Calculate Cutoff Time]
    V --> W[Count Old Records]
    W --> X{Old Data Exists?}
    X -->|No| Y[Log: No cleanup needed]
    X -->|Yes| Z[DELETE old records]
    Z --> AA[VACUUM database]
    AA --> BB[Log cleanup results]
    
    style A fill:#f3e5f5
    style L fill:#e8f5e8
    style U fill:#fff3e0
```

### Data Extraction Functions

```mermaid
graph TD
    A[_extract_airline_iata_code] --> B{Valid String?}
    B -->|No| C[return 'Unknown']
    B -->|Yes| D[Strip Whitespace]
    D --> E[Apply Regex Pattern]
    E --> F[^([A-Z]{2,3})\s*\d+]
    F --> G{Regex Match?}
    G -->|No| C
    G -->|Yes| H[Extract Group 1]
    H --> I{Length 2-3?}
    I -->|No| C
    I -->|Yes| J{All Alphabetic?}
    J -->|No| C
    J -->|Yes| K[return IATA Code]
    
    L[_store_airline_info] --> M[Extract Required Fields]
    M --> N{Record Exists?}
    N -->|Yes| O[UPDATE last_seen]
    N -->|No| P[INSERT OR IGNORE]
    O --> Q[Log Update]
    P --> R[Log Insert]
    
    S[_store_airport_info] --> T[Extract Airport Data]
    T --> U[Normalize Country Code]
    U --> V{Airport Exists?}
    V -->|Yes| W[UPDATE last_seen]
    V -->|No| X[INSERT OR IGNORE]
    W --> Y[Log Airport Update]
    X --> Z[Log Airport Insert]
    
    style A fill:#e3f2fd
    style L fill:#f1f8e9
    style S fill:#fce4ec
```

---

## 🔐 (Removed) Approval System Functions

The interactive approval workflow (search_flights_with_approval, request_api_approval, approve_and_execute, cost prompts) was removed in the September 2025 consolidation. The system now performs a direct cache-first search and only calls the external API when no fresh cached data exists.

If future governance or quota tracking is required, implement it as a non-blocking async metrics collector rather than an inline approval gate.

// Historic cost calculation diagrams removed (subsystem deprecated)

---

## 🗄️ Database Functions

### Core Database Operations

```mermaid
graph TD
    A[insert_api_response] --> B[Prepare Timestamp]
    B --> C[JSON Encode Parameters]
    C --> D[Calculate Response Size]
    D --> E[Execute INSERT SQL]
    E --> F[Get Last Row ID]
    F --> G[_update_metadata]
    G --> H[Commit Transaction]
    H --> I[return Record ID]
    
    J[get_api_responses] --> K[Build Query]
    K --> L[Apply Filters]
    L --> M[Add Ordering]
    M --> N[Execute Query]
    N --> O[Get Column Names]
    O --> P[Fetch All Rows]
    P --> Q[Format as Dictionaries]
    Q --> R[Parse JSON Fields]
    R --> S[return Results List]
    
    T[get_database_stats] --> U[Count Total Records]
    U --> V[Group by Type]
    V --> W[Calculate Date Range]
    W --> X[Get Metadata]
    X --> Y[Format Statistics]
    Y --> Z[return Stats Dictionary]
    
    style A fill:#e1f5fe
    style J fill:#f3e5f5
    style T fill:#fff3e0
```

### Cache-Specific Operations

```mermaid
graph TD
    A[_generate_cache_key] --> B[Normalize Parameters]
    B --> C[Convert to Lowercase]
    C --> D[Sort Keys]
    D --> E[JSON Serialize]
    E --> F[SHA256 Hash]
    F --> G[return Hex Digest]
    
    H[migrate_for_cache] --> I[Check Column Exists]
    I --> J{Cache Column Missing?}
    J -->|Yes| K[ALTER TABLE ADD cache_key]
    J -->|No| L[Cache Ready]
    K --> M[Create Indexes]
    M --> N[Update Existing Records]
    N --> O[Generate Cache Keys]
    O --> P[Commit Changes]
    
    Q[verify_cache_functionality] --> R[Test Cache Lookup]
    R --> S[Generate Test Key]
    S --> T[Execute Cache Query]
    T --> U[Check Results]
    U --> V[Count Cached Records]
    V --> W[return Verification Report]
    
    style A fill:#e8f5e8
    style H fill:#fff8e1
    style Q fill:#f3e5f5
```

---

## 🌐 API Client Functions

### Request Processing

```mermaid
graph TD
    A[_make_request] --> B[Apply Rate Limiting]
    B --> C[Build Headers]
    C --> D[Set Timeout]
    D --> E[Execute HTTP Request]
    E --> F{HTTP Success?}
    F -->|No| G[_handle_api_errors]
    F -->|Yes| H[Parse JSON Response]
    H --> I{JSON Valid?}
    I -->|No| J[return Parse Error]
    I -->|Yes| K[_parse_response]
    K --> L[return Structured Data]
    G --> M[Check Retry Logic]
    M --> N{Should Retry?}
    N -->|Yes| O[Wait and Retry]
    N -->|No| P[return Error Response]
    O --> E
    
    style A fill:#e1f5fe
    style G fill:#ffcdd2
    style K fill:#c8e6c9
```

### Parameter Validation

```mermaid
graph TD
    A[_validate_parameters] --> B[Check Required Fields]
    B --> C{departure_id valid?}
    C -->|No| D[Add to Error List]
    C -->|Yes| E[Check arrival_id]
    E --> F{arrival_id valid?}
    F -->|No| D
    F -->|Yes| G[Check Date Format]
    G --> H{Date valid?}
    H -->|No| D
    H -->|Yes| I[Check Passenger Counts]
    I --> J{Passengers valid?}
    J -->|No| D
    J -->|Yes| K[Check Optional Parameters]
    K --> L[Validate Currency]
    L --> M[Validate Travel Class]
    M --> N{All Valid?}
    N -->|Yes| O[return (True, [])]
    N -->|No| P[return (False, errors)]
    D --> P
    
    style A fill:#f3e5f5
    style O fill:#c8e6c9
    style P fill:#ffcdd2
```

### Response Parsing

```mermaid
graph TD
    A[_parse_response] --> B[Validate JSON Structure]
    B --> C{Valid Structure?}
    C -->|No| D[return Structure Error]
    C -->|Yes| E[Extract Flights Array]
    E --> F[Process Each Flight]
    F --> G[Extract Price Data]
    G --> H[Process Flight Segments]
    H --> I[Extract Airport Info]
    I --> J[Extract Airline Info]
    J --> K[Process Layovers]
    K --> L[Extract Metadata]
    L --> M[Calculate Totals]
    M --> N[Build Result Structure]
    N --> O[Validate Output]
    O --> P[return Parsed Data]
    
    style A fill:#e8f5e8
    style P fill:#c8e6c9
    style D fill:#ffcdd2
```

---

## 🔄 Integration Flow

### Complete Search Integration

```mermaid
graph TD
    User[👤 User Request] --> Entry[🚪 Entry Point]
    Entry --> Cache[💾 Cache Check]
    Cache --> CacheHit{🎯 Hit?}
    CacheHit -->|Yes| Fresh{🕐 Fresh?}
    Fresh -->|Yes| Return[📤 Return Data]
    Fresh -->|No| Clean[🧹 Cleanup]
  CacheHit -->|No| Clean[🧹 Cleanup]
  Clean --> API[🌐 Call API]
    API --> Success{✅ Success?}
    Success -->|Yes| Process[⚙️ Process Data]
  Success -->|No| Error[❌ Return Error]
  Process --> Store[💾 Store Results]
  Store --> Extract[🔤 Extract IATA]
  Extract --> UpdateRef[📊 Update References]
  UpdateRef --> Return
    
    style User fill:#e3f2fd
    style Return fill:#c8e6c9
    style Error fill:#ffcdd2
    style Reject fill:#ffcdd2
```

### Function Call Hierarchy

```mermaid
graph TD
  Main[CLI Invocation] --> Client[EnhancedFlightSearchClient]
    Client --> Search[search_flights]
    
    Search --> Validate[_validate_search_params]
    Search --> Cache[search_cache]
    Search --> API[SerpAPIFlightClient]
  Search --> WeekRange[search_week_range]
  Search --> Store[store_flight_data]
    
    Cache --> GenKey[_generate_cache_key]
    Cache --> Query[Database Query]
    
    API --> BuildURL[_build_search_url]
    API --> MakeReq[_make_request]
    API --> ParseResp[_parse_response]
    
    Store --> ExtractAirline[_extract_airline_iata_code]
    Store --> StoreAirline[_store_airline_info]
    Store --> StoreAirport[_store_airport_info]
    Store --> InsertAPI[insert_api_response]
    
    Validate --> CheckAirport[validate_airport_code]
    Validate --> CheckDate[validate_date_format]
    Validate --> CheckPass[validate_passenger_count]
    
    style Main fill:#e1f5fe
    style Client fill:#f3e5f5
    style Search fill:#e8f5e8
```

---

## 📈 Performance Function Map

### High-Performance Functions
- `search_cache()` - 5-15ms (indexed lookup)
- `_generate_cache_key()` - <1ms (hash calculation)
- `validate_airport_code()` - <1ms (regex check)

### Medium-Performance Functions  
- `store_flight_data()` - 50-200ms (multiple inserts)
- `cleanup_old_data()` - 100-500ms (batch operations)
- `_parse_response()` - 20-100ms (JSON processing)

### User-Interactive Functions
- `search_flights()` with API - 2-5 seconds (network call)

---

*This visual function map provides comprehensive flowcharts and diagrams for every major function in the SerpAPI Flight Search System, showing the complete execution flow and function relationships.*
