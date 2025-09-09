-- Auto-generated schema snapshot
-- Generated: 2025-09-08T14:24:34.106140
-- Tables: 12
-- Table List: airlines, airports, api_queries, database_metadata, flight_results, flight_searches, flight_segments, layovers, migration_history, price_insights, route_analytics, schema_version
-- Schema Checksum: 98115d8296267ed103fb319443654e904ecac41da00114a5d2e89a57d1c28d61

-- INDEX: idx_airlines_code
CREATE INDEX idx_airlines_code ON airlines(airline_code);

-- INDEX: idx_airports_code
CREATE INDEX idx_airports_code ON airports(airport_code);

-- INDEX: idx_created_at
CREATE INDEX idx_created_at ON api_queries(created_at);

-- INDEX: idx_flight_results_price
CREATE INDEX idx_flight_results_price ON flight_results(total_price);

-- INDEX: idx_flight_results_search_id
CREATE INDEX idx_flight_results_search_id ON flight_results(search_id);

-- INDEX: idx_flight_searches_airports
CREATE INDEX idx_flight_searches_airports ON flight_searches(departure_airport_code, arrival_airport_code);

-- INDEX: idx_flight_searches_cache_key
CREATE INDEX idx_flight_searches_cache_key ON flight_searches(cache_key);

-- INDEX: idx_flight_searches_date
CREATE INDEX idx_flight_searches_date ON flight_searches(outbound_date);

-- INDEX: idx_flight_searches_route_date
CREATE INDEX idx_flight_searches_route_date ON flight_searches(departure_airport_code, arrival_airport_code, outbound_date);

-- INDEX: idx_flight_searches_search_id
CREATE INDEX idx_flight_searches_search_id ON flight_searches(search_id);

-- INDEX: idx_flight_segments_airline
CREATE INDEX idx_flight_segments_airline ON flight_segments(airline_code);

-- INDEX: idx_flight_segments_airports
CREATE INDEX idx_flight_segments_airports ON flight_segments(departure_airport_code, arrival_airport_code);

-- INDEX: idx_flight_segments_result_id
CREATE INDEX idx_flight_segments_result_id ON flight_segments(flight_result_id);

-- INDEX: idx_layovers_airport
CREATE INDEX idx_layovers_airport ON layovers(airport_code);

-- INDEX: idx_layovers_result_id
CREATE INDEX idx_layovers_result_id ON layovers(flight_result_id);

-- INDEX: idx_price_insights_search_id
CREATE INDEX idx_price_insights_search_id ON price_insights(search_id);

-- INDEX: idx_price_insights_search_unique
CREATE UNIQUE INDEX idx_price_insights_search_unique ON price_insights(search_id);

-- INDEX: idx_query_type
CREATE INDEX idx_query_type ON api_queries(query_type);

-- INDEX: idx_route_analytics_airports
CREATE INDEX idx_route_analytics_airports ON route_analytics(departure_airport_code, arrival_airport_code);

-- INDEX: idx_route_analytics_route
CREATE INDEX idx_route_analytics_route ON route_analytics(route_key);

-- TABLE: airlines
CREATE TABLE airlines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    airline_code TEXT UNIQUE NOT NULL,
    airline_name TEXT NOT NULL,
    logo_url TEXT,
    alliance TEXT, -- STAR_ALLIANCE, SKYTEAM, ONEWORLD
    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- TABLE: airports
CREATE TABLE airports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    airport_code TEXT UNIQUE NOT NULL,
    airport_name TEXT NOT NULL,
    city TEXT,
    country TEXT,
    country_code TEXT,
    timezone TEXT
);

-- TABLE: api_queries
CREATE TABLE "api_queries" (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_parameters TEXT,
                    raw_response TEXT NOT NULL,
                    query_type TEXT,
                    status_code INTEGER,
                    response_size INTEGER,
                    api_endpoint TEXT,
                    search_term TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

-- TABLE: database_metadata
CREATE TABLE database_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                database_version TEXT,
                created_date TEXT,
                last_modified TEXT,
                total_queries INTEGER DEFAULT 0
            );

-- TABLE: flight_results
CREATE TABLE flight_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_id TEXT NOT NULL,
    result_type TEXT NOT NULL, -- 'best_flight' or 'other_flight'
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
    airline_logo_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (search_id) REFERENCES flight_searches(search_id)
);

-- TABLE: flight_searches
CREATE TABLE flight_searches (
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

-- TABLE: flight_segments
CREATE TABLE flight_segments (
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

-- TABLE: layovers
CREATE TABLE layovers (
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

-- TABLE: migration_history
CREATE TABLE migration_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL,
                    applied_at TEXT NOT NULL,
                    description TEXT,
                    checksum TEXT
                );

-- TABLE: price_insights
CREATE TABLE price_insights (
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

-- TABLE: route_analytics
CREATE TABLE route_analytics (
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

-- TABLE: schema_version
CREATE TABLE schema_version (id INTEGER PRIMARY KEY CHECK(id=1), version TEXT NOT NULL, applied_at TEXT NOT NULL);
