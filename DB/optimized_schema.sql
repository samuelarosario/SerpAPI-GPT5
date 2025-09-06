-- OPTIMIZED Database Schema for SerpAPI Google Flights Data
-- Eliminates redundancy by using proper foreign key relationships

-- Airports Table (Reference data) - NORMALIZED
CREATE TABLE IF NOT EXISTS airports (
    airport_code TEXT PRIMARY KEY, -- Use airport code as primary key
    airport_name TEXT NOT NULL,
    city TEXT,
    country TEXT,
    country_code TEXT,
    timezone TEXT,
    image_url TEXT,
    thumbnail_url TEXT,
    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Airlines Table (Reference data) - NORMALIZED  
CREATE TABLE IF NOT EXISTS airlines (
    airline_code TEXT PRIMARY KEY, -- Use airline code as primary key
    airline_name TEXT NOT NULL,
    logo_url TEXT,
    alliance TEXT, -- STAR_ALLIANCE, SKYTEAM, ONEWORLD
    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Flight Search Queries Table - OPTIMIZED
CREATE TABLE IF NOT EXISTS flight_searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_id TEXT UNIQUE NOT NULL,
    search_timestamp TEXT NOT NULL,
    departure_airport_code TEXT NOT NULL, -- FK to airports
    arrival_airport_code TEXT NOT NULL,   -- FK to airports
    outbound_date TEXT,
    return_date TEXT,
    flight_type INTEGER DEFAULT 1, -- 1=Round trip, 2=One way, 3=Multi-city
    adults INTEGER DEFAULT 1,
    children INTEGER DEFAULT 0,
    infants_in_seat INTEGER DEFAULT 0,
    infants_on_lap INTEGER DEFAULT 0,
    travel_class INTEGER DEFAULT 1, -- 1=Economy, 2=Premium, 3=Business, 4=First
    currency TEXT DEFAULT 'USD',
    country_code TEXT DEFAULT 'us',
    language_code TEXT DEFAULT 'en',
    max_price INTEGER,
    stops INTEGER,
    deep_search BOOLEAN DEFAULT FALSE,
    show_hidden BOOLEAN DEFAULT FALSE,
    raw_parameters TEXT, -- JSON of all search parameters
    response_status TEXT,
    total_results INTEGER DEFAULT 0,
    cache_key TEXT, -- SHA256 hash of normalized search parameters for caching
    api_query_id INTEGER, -- Reference to original api_queries table
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (departure_airport_code) REFERENCES airports(airport_code),
    FOREIGN KEY (arrival_airport_code) REFERENCES airports(airport_code),
    FOREIGN KEY (api_query_id) REFERENCES api_queries(id)
);

-- Flight Results Table (Individual flight options) - OPTIMIZED
CREATE TABLE IF NOT EXISTS flight_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_id TEXT NOT NULL,
    result_type TEXT NOT NULL, -- 'best', 'other'
    result_rank INTEGER,
    total_duration INTEGER, -- Total minutes including layovers
    total_price INTEGER, -- Price in search currency
    price_currency TEXT,
    flight_type TEXT, -- 'Round trip', 'One way', 'Multi-city'
    layover_count INTEGER DEFAULT 0,
    carbon_emissions_flight INTEGER,
    carbon_emissions_typical INTEGER,
    carbon_emissions_difference_percent INTEGER,
    departure_token TEXT,
    booking_token TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (search_id) REFERENCES flight_searches(search_id)
);

-- Individual Flight Segments Table - OPTIMIZED (Eliminates redundancy)
CREATE TABLE IF NOT EXISTS flight_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_result_id INTEGER NOT NULL,
    segment_order INTEGER NOT NULL, -- Order within the flight result
    departure_airport_code TEXT NOT NULL, -- FK to airports (NO redundant name)
    departure_time TEXT NOT NULL,
    arrival_airport_code TEXT NOT NULL,   -- FK to airports (NO redundant name)
    arrival_time TEXT NOT NULL,
    duration_minutes INTEGER,
    airplane_model TEXT,
    airline_code TEXT NOT NULL,           -- FK to airlines (NO redundant name/logo)
    flight_number TEXT,
    travel_class TEXT,
    legroom TEXT,
    is_overnight BOOLEAN DEFAULT FALSE,
    often_delayed BOOLEAN DEFAULT FALSE,
    ticket_also_sold_by TEXT, -- JSON array of other sellers
    extensions TEXT, -- JSON array of flight features
    plane_and_crew_by TEXT,
    carbon_emissions INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (flight_result_id) REFERENCES flight_results(id),
    FOREIGN KEY (departure_airport_code) REFERENCES airports(airport_code),
    FOREIGN KEY (arrival_airport_code) REFERENCES airports(airport_code),
    FOREIGN KEY (airline_code) REFERENCES airlines(airline_code)
);

-- Layovers Table - OPTIMIZED
CREATE TABLE IF NOT EXISTS layovers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_result_id INTEGER NOT NULL,
    layover_order INTEGER NOT NULL,
    airport_code TEXT NOT NULL,        -- FK to airports (NO redundant name)
    duration_minutes INTEGER,
    is_overnight BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (flight_result_id) REFERENCES flight_results(id),
    FOREIGN KEY (airport_code) REFERENCES airports(airport_code)
);

-- Price Insights Table - NO CHANGES NEEDED
CREATE TABLE IF NOT EXISTS price_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_id TEXT NOT NULL,
    lowest_price INTEGER,
    price_level TEXT, -- 'low', 'high', 'typical'
    typical_price_low INTEGER,
    typical_price_high INTEGER,
    price_history TEXT, -- JSON array of [timestamp, price] pairs
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (search_id) REFERENCES flight_searches(search_id)
);

-- Route Analytics Table - OPTIMIZED
CREATE TABLE IF NOT EXISTS route_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_key TEXT UNIQUE NOT NULL, -- "departure_code-arrival_code"
    departure_airport_code TEXT NOT NULL, -- FK to airports
    arrival_airport_code TEXT NOT NULL,   -- FK to airports
    total_searches INTEGER DEFAULT 1,
    avg_price INTEGER,
    min_price INTEGER,
    max_price INTEGER,
    last_search_date TEXT,
    price_trend TEXT, -- 'increasing', 'decreasing', 'stable'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (departure_airport_code) REFERENCES airports(airport_code),
    FOREIGN KEY (arrival_airport_code) REFERENCES airports(airport_code)
);

-- Create optimized indexes for performance
CREATE INDEX IF NOT EXISTS idx_flight_searches_search_id ON flight_searches(search_id);
CREATE INDEX IF NOT EXISTS idx_flight_searches_airports ON flight_searches(departure_airport_code, arrival_airport_code);
CREATE INDEX IF NOT EXISTS idx_flight_searches_date ON flight_searches(outbound_date);
CREATE INDEX IF NOT EXISTS idx_flight_results_search_id ON flight_results(search_id);
CREATE INDEX IF NOT EXISTS idx_flight_results_price ON flight_results(total_price);
CREATE INDEX IF NOT EXISTS idx_flight_segments_result_id ON flight_segments(flight_result_id);
CREATE INDEX IF NOT EXISTS idx_flight_segments_airports ON flight_segments(departure_airport_code, arrival_airport_code);
CREATE INDEX IF NOT EXISTS idx_flight_segments_airline ON flight_segments(airline_code);
CREATE INDEX IF NOT EXISTS idx_layovers_result_id ON layovers(flight_result_id);
CREATE INDEX IF NOT EXISTS idx_layovers_airport ON layovers(airport_code);
CREATE INDEX IF NOT EXISTS idx_price_insights_search_id ON price_insights(search_id);
CREATE INDEX IF NOT EXISTS idx_route_analytics_route ON route_analytics(route_key);
CREATE INDEX IF NOT EXISTS idx_route_analytics_airports ON route_analytics(departure_airport_code, arrival_airport_code);

-- OPTIMIZATION BENEFITS:
-- 1. ELIMINATED REDUNDANCY: No more duplicate airport/airline names
-- 2. REFERENTIAL INTEGRITY: Proper foreign key constraints
-- 3. STORAGE EFFICIENCY: Significantly reduced storage space
-- 4. DATA CONSISTENCY: Single source of truth for airport/airline data
-- 5. QUERY PERFORMANCE: Better indexing with code-based lookups
-- 6. MAINTENANCE: Updates to airport/airline info only need to happen in one place
