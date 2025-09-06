# Flight Search to Flight Segments Relationship Mapping

## 🔗 **Database Relationship Hierarchy**

The system uses a **three-tier relationship** to link flight searches to individual flight segments:

```
flight_searches (search parameters)
       │
       │ (1 : Many)
       ▼
flight_results (individual flight options)
       │
       │ (1 : Many) 
       ▼
flight_segments (individual flight legs)
```

## 📋 **Detailed Relationship Structure**

### **Level 1: Flight Searches Table**
```sql
CREATE TABLE flight_searches (
    id INTEGER PRIMARY KEY,
    search_id TEXT UNIQUE,              -- "search_20250906_155046_9aab409060c9"
    departure_airport_code TEXT,        -- "POM"
    arrival_airport_code TEXT,          -- "MNL"
    outbound_date TEXT,                 -- "2025-09-27"
    cache_key TEXT,                     -- SHA256 hash for caching
    -- ... other search parameters
)
```

### **Level 2: Flight Results Table** 
```sql
CREATE TABLE flight_results (
    id INTEGER PRIMARY KEY,             -- Auto-increment ID
    search_id TEXT,                     -- FK to flight_searches.search_id
    total_price INTEGER,                -- $1391
    total_duration INTEGER,             -- 830 minutes
    result_type TEXT,                   -- "best_flight" or "other_flight"
    -- ... other flight-level data
    FOREIGN KEY (search_id) REFERENCES flight_searches(search_id)
)
```

### **Level 3: Flight Segments Table**
```sql
CREATE TABLE flight_segments (
    id INTEGER PRIMARY KEY,
    flight_result_id INTEGER,           -- FK to flight_results.id
    segment_order INTEGER,              -- 1, 2, 3... (order within flight)
    departure_airport_code TEXT,        -- "POM", "SYD", etc.
    arrival_airport_code TEXT,          -- "SYD", "MNL", etc.
    airline_code TEXT,                  -- "QF" (Qantas)
    flight_number TEXT,                 -- "QF 58"
    departure_time TEXT,                -- "2025-09-27 13:15"
    arrival_time TEXT,                  -- "2025-09-27 16:20"
    -- ... other segment details
    FOREIGN KEY (flight_result_id) REFERENCES flight_results(id)
)
```

## 🔧 **How the Linking Works in Code**

### **Step 1: Store Flight Search**
```python
# Create flight search record
cursor.execute("INSERT INTO flight_searches (...) VALUES (...)", search_params)
search_id = "search_20250906_155046_9aab409060c9"  # Generated ID
```

### **Step 2: Store Each Flight Result**
```python
for flight in api_response['best_flights']:
    cursor.execute("""
        INSERT INTO flight_results (search_id, total_price, ...)
        VALUES (?, ?, ...)
    """, (search_id, flight['price'], ...))
    
    flight_result_id = cursor.lastrowid  # Get auto-generated ID (e.g., 42)
```

### **Step 3: Store Flight Segments**
```python
    # For each segment in this flight result
    for segment_order, segment in enumerate(flight['flights'], 1):
        cursor.execute("""
            INSERT INTO flight_segments (flight_result_id, segment_order, ...)
            VALUES (?, ?, ...)
        """, (flight_result_id, segment_order, ...))
```

## 📊 **Example Data Flow**

### **Real Example from Sep 27 Search:**

**Flight Search:**
- `search_id`: "search_20250906_155046_9aab409060c9"
- Route: POM → MNL
- Date: 2025-09-27

**Flight Result:**
- `id`: 42 (auto-generated)
- `search_id`: "search_20250906_155046_9aab409060c9"
- `total_price`: 1391
- `total_duration`: 830

**Flight Segments:**
```
Segment 1:
- flight_result_id: 42
- segment_order: 1
- route: POM → SYD (QF 58)
- time: 13:15 → 16:20

Segment 2:  
- flight_result_id: 42
- segment_order: 2
- route: SYD → MNL (QF 97)
- time: 19:15 → 01:05+1
```

## 🔍 **Query to Retrieve Complete Flight Data**

```sql
SELECT 
    fs.search_id,
    fs.departure_airport_code,
    fs.arrival_airport_code,
    fr.total_price,
    fr.total_duration,
    seg.segment_order,
    seg.departure_airport_code as seg_departure,
    seg.arrival_airport_code as seg_arrival,
    seg.airline_code,
    seg.flight_number,
    seg.departure_time,
    seg.arrival_time
FROM flight_searches fs
JOIN flight_results fr ON fs.search_id = fr.search_id
JOIN flight_segments seg ON fr.id = seg.flight_result_id
WHERE fs.search_id = 'search_20250906_155046_9aab409060c9'
ORDER BY fr.total_price, seg.segment_order;
```

## 🎯 **Key Benefits of This Structure**

1. **Normalization**: No data duplication
2. **Flexibility**: Multi-segment flights (connecting flights)
3. **Referential Integrity**: Foreign key constraints ensure data consistency
4. **Scalability**: Can handle complex multi-city routes
5. **Analytics**: Easy to query by route, price, airline, etc.
6. **Caching**: Search-level caching with detailed segment retrieval

## ⚡ **Cache Retrieval Process**

When using cached data:
1. **Find flight search** by cache_key
2. **Get flight results** using search_id 
3. **Get flight segments** using flight_result_id
4. **Reconstruct** complete flight information with airport/airline names from reference tables

This three-tier relationship allows the system to efficiently store, cache, and retrieve complex flight data while maintaining data integrity and supporting sophisticated queries.
