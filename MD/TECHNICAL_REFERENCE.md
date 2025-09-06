# SerpAPI System - Technical Function Reference

## � SCHEMA MODIFICATION WARNING

**⚠️ DATABASE SCHEMA CHANGES ARE STRICTLY PROHIBITED ⚠️**

Any modifications to the database schema require explicit double-confirmation from the project owner. Unauthorized schema changes can break the entire system and compromise data integrity. Only data operations (INSERT, UPDATE, DELETE) are permitted without special approval.

---

## �📋 Complete Function Documentation with Flow Diagrams

---

## 🔍 Enhanced Flight Search Client Functions

### 1. `search_flights()` - Main Search Function

```mermaid
sequenceDiagram
    participant U as User
    participant ESC as EnhancedFlightSearchClient
    participant V as Validator
    participant C as Cache
    participant API as SerpAPIClient
    participant DB as Database
    
    U->>ESC: search_flights(params)
    ESC->>ESC: cleanup_old_data()
    ESC->>ESC: build_search_params()
    ESC->>ESC: auto_generate_return_date()
    ESC->>V: _validate_search_params()
    V-->>ESC: validation_result
    
    alt Validation Failed
        ESC-->>U: return validation_error
    else Validation Passed
        ESC->>C: search_cache()
        alt Cache Hit
            C-->>ESC: cached_data
            ESC-->>U: return cached_result
        else Cache Miss
            ESC->>API: search_round_trip() / search_one_way()
            API-->>ESC: api_result
            alt API Success
                ESC->>DB: store_flight_data()
                ESC->>ESC: _store_airline_info()
                ESC->>ESC: _store_airport_info()
                ESC-->>U: return api_result
            else API Failed
                ESC-->>U: return api_error
            end
        end
    end
```

**Function Details:**
- **Purpose**: Smart flight search with cache-first strategy
- **Parameters**: 12 main parameters including departure_id, arrival_id, dates, passengers
- **Returns**: Standardized result dict with success, source, data, and metadata
- **Cache Strategy**: Checks 24-hour cache before API calls
- **Auto-features**: Auto-generates return dates, auto-validates parameters

### 2. `_extract_airline_iata_code()` - IATA Code Extraction

```mermaid
flowchart TD
    Start([Flight Number Input]) --> ValidateInput{Valid String?}
    ValidateInput -->|No| DefaultReturn[Return 'Unknown']
    ValidateInput -->|Yes| StripWhitespace[Strip Whitespace]
    
    StripWhitespace --> ApplyRegex[Apply Regex: ^([A-Z]{2,3})\s*\d+]
    ApplyRegex --> RegexMatch{Match Found?}
    
    RegexMatch -->|No| DefaultReturn
    RegexMatch -->|Yes| ExtractGroup[Extract Group 1]
    
    ExtractGroup --> ValidateLength{Length 2-3 Chars?}
    ValidateLength -->|No| DefaultReturn
    ValidateLength -->|Yes| ValidateAlpha{All Alphabetic?}
    
    ValidateAlpha -->|No| DefaultReturn
    ValidateAlpha -->|Yes| ReturnIATA[Return IATA Code]
    
    DefaultReturn --> End([End])
    ReturnIATA --> End
```

**Function Details:**
- **Purpose**: Extract 2-3 character airline IATA codes from flight numbers
- **Input**: Flight number string (e.g., "PR 216", "CX 123")
- **Output**: IATA code (e.g., "PR", "CX") or "Unknown"
- **Regex Pattern**: `^([A-Z]{2,3})\s*\d+` - Matches airline code followed by numbers
- **Validation**: Ensures extracted code is 2-3 alphabetic characters

### 3. `_store_airline_info()` & `_store_airport_info()` - Reference Data Management

```mermaid
flowchart TD
    Start([Store Reference Data]) --> ExtractData[Extract Required Fields]
    ExtractData --> CheckExists{Record Exists?}
    
    CheckExists -->|Yes| UpdateTimestamp[UPDATE last_seen]
    CheckExists -->|No| InsertRecord[INSERT OR IGNORE new record]
    
    UpdateTimestamp --> LogUpdate[Log Update Action]
    InsertRecord --> LogInsert[Log Insert Action]
    
    LogUpdate --> End([End])
    LogInsert --> End
```

**Function Details:**
- **Purpose**: Maintain normalized reference tables for airports and airlines
- **Strategy**: INSERT OR IGNORE + UPDATE pattern for upsert functionality
- **Tracking**: Updates last_seen timestamps for existing records
- **Logging**: Comprehensive logging of all database operations

---

## 🔐 API Approval System Functions

### 1. `request_api_approval()` - Main Approval Function

```mermaid
sequenceDiagram
    participant C as Client
    participant AS as APICallMonitor
    participant U as User
    participant L as Logger
    
    C->>AS: request_api_approval(params, reason)
    AS->>AS: _load_call_history()
    AS->>AS: _calculate_cost(params)
    AS->>AS: _generate_search_id()
    AS->>AS: create_approval_request()
    
    AS->>U: display_approval_prompt()
    Note over U: Shows cost, usage stats, parameters
    U->>AS: user_input (y/n)
    
    alt User Approves
        AS->>L: log_approved_call()
        AS->>AS: _update_usage_stats()
        AS-->>C: return (True, request)
    else User Rejects
        AS->>L: log_rejected_call()
        AS-->>C: return (False, request)
    end
```

**Function Details:**
- **Purpose**: Interactive approval system for API calls with cost management
- **Cost Calculation**: $0.05 per flight search with daily usage tracking
- **User Interface**: Formatted prompt showing cost, usage, and parameters
- **Logging**: Complete audit trail of all approval decisions
- **Return**: Tuple of (should_proceed: bool, request: APICallRequest)

### 2. `generate_usage_report()` - Usage Analytics

```mermaid
flowchart TD
    Start([Generate Report]) --> LoadHistory[Load Call History]
    LoadHistory --> FilterToday[Filter Today's Calls]
    FilterToday --> CountCalls[Count Total Calls]
    CountCalls --> CalcCost[Calculate Total Cost]
    
    CalcCost --> GroupByType[Group by Call Type]
    GroupByType --> CalcStats[Calculate Statistics]
    CalcStats --> FormatReport[Format Report String]
    
    FormatReport --> AddTimestamp[Add Timestamp]
    AddTimestamp --> ReturnReport[Return Formatted Report]
    
    ReturnReport --> End([End])
```

**Function Details:**
- **Purpose**: Generate comprehensive usage analytics for cost tracking
- **Metrics**: Total calls, cost breakdown, calls by type, daily trends
- **Format**: Human-readable string with emoji formatting
- **Time Range**: Configurable time periods (default: daily)

---

## 💾 Database Functions

### 1. `FlightSearchCache.search_cache()` - Cache Lookup

```mermaid
flowchart TD
    Start([Cache Search Request]) --> NormalizeParams[Normalize Parameters]
    NormalizeParams --> GenerateKey[Generate SHA256 Key]
    GenerateKey --> CalcCutoff[Calculate 24h Cutoff]
    
    CalcCutoff --> QueryDB[Query Database with Key + Time]
    QueryDB --> RecordFound{Record Found?}
    
    RecordFound -->|No| ReturnNone[Return None - Cache Miss]
    RecordFound -->|Yes| ParseJSON[Parse JSON Response]
    
    ParseJSON --> AddMetadata[Add Cache Metadata]
    AddMetadata --> ReturnData[Return Cached Data]
    
    ReturnNone --> End([End])
    ReturnData --> End
```

**SQL Query Used:**
```sql
SELECT fs.*, ar.raw_response, ar.query_timestamp
FROM flight_searches fs
JOIN api_queries ar ON fs.search_id = ar.search_term
WHERE fs.cache_key = ? 
  AND ar.query_timestamp > ?
ORDER BY ar.query_timestamp DESC
LIMIT 1
```

### 2. `store_flight_data()` - Data Persistence

```mermaid
flowchart TD
    Start([Store Flight Data]) --> BeginTx[Begin Transaction]
    BeginTx --> StoreSearchRecord[Store flight_searches Record]
    StoreSearchRecord --> ProcessFlights[Process Each Flight]
    
    ProcessFlights --> StoreFlightResult[Store flight_results Record]
    StoreFlightResult --> ProcessSegments[Process Flight Segments]
    ProcessSegments --> ExtractAirportData[Extract Airport Data]
    ExtractAirportData --> ExtractAirlineData[Extract Airline Data]
    
    ExtractAirlineData --> ExtractIATACodes[Extract IATA Codes]
    ExtractIATACodes --> StoreSegmentRecord[Store flight_segments Record]
    StoreSegmentRecord --> UpdateReferences[Update Reference Tables]
    
    UpdateReferences --> StoreRawAPI[Store Raw API Response]
    StoreRawAPI --> CommitTx[Commit Transaction]
    CommitTx --> UpdateIndexes[Update Database Indexes]
    
    UpdateIndexes --> End([Storage Complete])
```

**Function Details:**
- **Atomic Operations**: Full transaction support with rollback on errors
- **Data Integrity**: Foreign key constraints maintained throughout
- **Reference Updates**: Automatic upsert of airports and airlines tables
- **Raw Preservation**: Complete API response stored for future analysis
- **Index Maintenance**: Automatic index updates for performance

### 3. `cleanup_old_data()` - Cache Maintenance

```mermaid
flowchart TD
    Start([Cleanup Request]) --> CalcCutoff[Calculate Cutoff Time]
    CalcCutoff --> CountOld[Count Old Records]
    CountOld --> HasOldData{Old Data Exists?}
    
    HasOldData -->|No| LogNoCleanup[Log: No cleanup needed]
    HasOldData -->|Yes| DeleteOldSearches[DELETE old flight_searches]
    
    DeleteOldSearches --> DeleteOldQueries[DELETE old api_queries]
    DeleteOldQueries --> DeleteOrphaned[DELETE orphaned records]
    DeleteOrphaned --> VacuumDB[VACUUM database]
    
    VacuumDB --> LogCleanup[Log cleanup results]
    LogCleanup --> End([Cleanup Complete])
    LogNoCleanup --> End
```

**SQL Operations:**
```sql
-- Delete old flight searches (>24 hours)
DELETE FROM flight_searches 
WHERE search_timestamp < ?

-- Delete old API queries (>24 hours)  
DELETE FROM api_queries 
WHERE query_timestamp < ?

-- Clean up orphaned records
DELETE FROM flight_results 
WHERE search_id NOT IN (SELECT search_id FROM flight_searches)
```

---

## 🌐 SerpAPI Client Functions

### 1. `search_round_trip()` - Round-trip Flight Search

```mermaid
sequenceDiagram
    participant C as Client
    participant SC as SerpAPIClient
    participant RL as RateLimiter
    participant API as SerpAPI
    participant P as Parser
    
    C->>SC: search_round_trip(params)
    SC->>SC: _validate_parameters(params)
    SC->>SC: _build_search_url(params)
    SC->>RL: check_rate_limit()
    RL-->>SC: rate_limit_ok
    
    SC->>API: HTTP GET request
    API-->>SC: JSON response
    SC->>SC: _handle_api_errors(response)
    SC->>P: _parse_response(response)
    P-->>SC: structured_data
    SC-->>C: return formatted_result
```

**Function Details:**
- **Parameter Validation**: Comprehensive validation of all 25+ parameters
- **URL Building**: Dynamic URL construction with proper encoding
- **Rate Limiting**: Built-in rate limiting to respect API limits
- **Error Handling**: HTTP and API error handling with retries
- **Response Parsing**: Structured parsing of complex JSON responses

### 2. `_parse_response()` - Response Processing

```mermaid
flowchart TD
    Start([API Response]) --> ValidateJSON{Valid JSON?}
    ValidateJSON -->|No| ErrorReturn[Return Parse Error]
    ValidateJSON -->|Yes| CheckStructure{Expected Structure?}
    
    CheckStructure -->|No| StructureError[Return Structure Error]
    CheckStructure -->|Yes| ExtractFlights[Extract Flight Data]
    
    ExtractFlights --> ProcessPricing[Process Pricing Info]
    ProcessPricing --> ProcessSegments[Process Flight Segments]
    ProcessSegments --> ProcessAirports[Process Airport Data]
    ProcessAirports --> ProcessAirlines[Process Airline Data]
    
    ProcessAirlines --> ExtractMetadata[Extract Search Metadata]
    ExtractMetadata --> BuildResult[Build Structured Result]
    BuildResult --> ValidateOutput[Validate Output Structure]
    
    ValidateOutput --> ReturnSuccess[Return Parsed Data]
    ErrorReturn --> End([End])
    StructureError --> End
    ReturnSuccess --> End
```

**Key Extraction Patterns:**
- **Flights**: `response['flights']` array processing
- **Prices**: Currency normalization and price extraction
- **Segments**: Departure/arrival times, airports, airlines
- **Metadata**: Search tokens, booking URLs, carbon emissions

---

## 🔄 Integration Patterns

### 1. Cache-First Search Pattern

```mermaid
flowchart LR
    Request --> Cache{Cache?}
    Cache -->|Hit| ValidateAge{Fresh?}
    ValidateAge -->|Yes| Return[Return Cached]
    ValidateAge -->|No| API[Call API]
    Cache -->|Miss| API
    API --> Store[Store Result]
    Store --> Return
```

### 2. Approval Workflow Pattern

```mermaid
flowchart LR
    APIRequest --> CheckApproval{Approval Needed?}
    CheckApproval -->|No| Execute[Execute API]
    CheckApproval -->|Yes| RequestApproval[Request User Approval]
    RequestApproval --> UserDecision{User Choice}
    UserDecision -->|Approve| Execute
    UserDecision -->|Reject| Cancel[Cancel Request]
    Execute --> LogCall[Log API Call]
    Cancel --> LogReject[Log Rejection]
```

### 3. Database Transaction Pattern

```mermaid
flowchart LR
    Begin[BEGIN TRANSACTION] --> Operations[Execute Operations]
    Operations --> Check{All Success?}
    Check -->|Yes| Commit[COMMIT]
    Check -->|No| Rollback[ROLLBACK]
    Commit --> UpdateIndexes[Update Indexes]
    Rollback --> LogError[Log Error]
```

---

## 🎯 Function Dependencies

```mermaid
graph TD
    ESC[EnhancedFlightSearchClient] --> |uses| SAC[SerpAPIFlightClient]
    ESC --> |uses| FSC[FlightSearchCache]
    ESC --> |uses| FSV[FlightSearchValidator]
    
    ARSC[ApprovalRequiredSearchClient] --> |wraps| ESC
    ARSC --> |uses| ACM[APICallMonitor]
    
    FSC --> |uses| SADB[SerpAPIDatabase]
    ACM --> |uses| SADB
    
    SAC --> |uses| RL[RateLimiter]
    SAC --> |calls| SAPI[SerpAPI Service]
    
    SADB --> |stores in| DB[(SQLite Database)]
```

---

## 📊 Performance Metrics

### Function Execution Times (Typical)
- `search_cache()`: 5-15ms (database query)
- `search_flights()` (cache hit): 20-50ms
- `search_flights()` (API call): 2-5 seconds
- `store_flight_data()`: 50-200ms
- `request_api_approval()`: User-dependent
- `cleanup_old_data()`: 100-500ms

### Database Operations
- **Cache lookup**: Single indexed query
- **Data storage**: 5-15 INSERT operations per flight search
- **Cleanup**: Batch DELETE operations with VACUUM
- **Reference updates**: UPSERT pattern for efficiency

---

*This technical reference documents the complete function architecture of the SerpAPI Flight Search System, including detailed flow diagrams for each major component.*
