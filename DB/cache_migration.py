"""
Database Migration: Add Cache Key Support
Adds cache_key column to flight_searches table for enhanced search caching
"""

import sqlite3
import os
import logging

def migrate_database_for_cache_support(db_path: str = "Main_DB.db"):
    """
    Add cache_key column to flight_searches table for enhanced caching
    
    Args:
        db_path: Path to the SQLite database file
    """
    
    try:
        # Connect to database
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check if cache_key column already exists
            cursor.execute("PRAGMA table_info(flight_searches)")
            columns = cursor.fetchall()
            column_names = [column[1] for column in columns]
            
            if 'cache_key' not in column_names:
                print("Adding cache_key column to flight_searches table...")
                
                # Add cache_key column
                cursor.execute("""
                ALTER TABLE flight_searches 
                ADD COLUMN cache_key TEXT
                """)
                
                # Create index for faster cache lookups
                cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_flight_searches_cache_key 
                ON flight_searches(cache_key)
                """)
                
                # Create composite index for cache lookups with timestamp
                cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_lookup 
                ON flight_searches(cache_key, search_timestamp)
                """)
                
                conn.commit()
                print("✅ Successfully added cache_key column and indexes")
                
                # Update existing records with cache keys if any exist
                cursor.execute("SELECT COUNT(*) FROM flight_searches")
                existing_count = cursor.fetchone()[0]
                
                if existing_count > 0:
                    print(f"Found {existing_count} existing flight searches")
                    print("Generating cache keys for existing records...")
                    
                    # Get all existing records
                    cursor.execute("""
                    SELECT id, search_id, raw_parameters 
                    FROM flight_searches 
                    WHERE cache_key IS NULL
                    """)
                    
                    records = cursor.fetchall()
                    
                    # Generate cache keys for existing records
                    import json
                    import hashlib
                    
                    updated_count = 0
                    for record_id, search_id, raw_parameters in records:
                        try:
                            if raw_parameters:
                                # Parse and normalize parameters
                                params = json.loads(raw_parameters)
                                normalized_params = {}
                                
                                for key, value in params.items():
                                    if value is not None:
                                        normalized_params[key] = str(value).lower() if isinstance(value, str) else value
                                
                                # Generate cache key
                                param_string = json.dumps(normalized_params, sort_keys=True)
                                cache_key = hashlib.sha256(param_string.encode()).hexdigest()
                                
                                # Update record
                                cursor.execute("""
                                UPDATE flight_searches 
                                SET cache_key = ? 
                                WHERE id = ?
                                """, (cache_key, record_id))
                                
                                updated_count += 1
                                
                        except Exception as e:
                            print(f"Warning: Could not generate cache key for search {search_id}: {e}")
                    
                    conn.commit()
                    print(f"✅ Updated {updated_count} existing records with cache keys")
                
            else:
                print("✅ cache_key column already exists - no migration needed")
            
            # Verify the migration
            cursor.execute("PRAGMA table_info(flight_searches)")
            columns = cursor.fetchall()
            cache_column = next((col for col in columns if col[1] == 'cache_key'), None)
            
            if cache_column:
                print(f"✅ Verified: cache_key column exists with type: {cache_column[2]}")
            
            # Check indexes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='flight_searches'")
            indexes = cursor.fetchall()
            print(f"✅ Flight searches table indexes: {[idx[0] for idx in indexes]}")
            
            print("🎯 Database migration completed successfully!")
            
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        raise

def verify_cache_functionality(db_path: str = "Main_DB.db"):
    """
    Verify that cache functionality is working properly
    
    Args:
        db_path: Path to the SQLite database file
    """
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            print("\n🔍 Verifying cache functionality...")
            
            # Test cache key generation and lookup
            test_params = {
                'departure_id': 'LAX',
                'arrival_id': 'JFK',
                'outbound_date': '2025-09-15',
                'adults': 2,
                'currency': 'USD'
            }
            
            # Generate test cache key
            import json
            import hashlib
            
            normalized_params = {}
            for key, value in test_params.items():
                if value is not None:
                    normalized_params[key] = str(value).lower() if isinstance(value, str) else value
            
            param_string = json.dumps(normalized_params, sort_keys=True)
            test_cache_key = hashlib.sha256(param_string.encode()).hexdigest()
            
            print(f"Generated test cache key: {test_cache_key[:16]}...")
            
            # Test cache lookup query
            from datetime import datetime, timedelta
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            query = """
            SELECT fs.*, ar.raw_response, ar.query_timestamp
            FROM flight_searches fs
            JOIN api_queries ar ON fs.search_id = ar.search_term
            WHERE fs.cache_key = ? 
            AND ar.query_timestamp > ?
            ORDER BY ar.query_timestamp DESC
            LIMIT 1
            """
            
            cursor.execute(query, (test_cache_key, cutoff_time.isoformat()))
            result = cursor.fetchone()
            
            if result:
                print("✅ Cache lookup query working - found existing data")
            else:
                print("✅ Cache lookup query working - no matching data (expected for test)")
            
            # Check current cache statistics
            cursor.execute("SELECT COUNT(*) FROM flight_searches WHERE cache_key IS NOT NULL")
            cached_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM flight_searches")
            total_count = cursor.fetchone()[0]
            
            print(f"✅ Cache statistics: {cached_count}/{total_count} searches have cache keys")
            
            print("🎯 Cache functionality verification completed!")
            
    except Exception as e:
        print(f"❌ Cache verification failed: {str(e)}")
        raise

if __name__ == "__main__":
    """Run the migration when script is executed directly"""
    
    print("🚀 Starting Database Migration for Enhanced Flight Search Cache")
    print("=" * 60)
    
    try:
        # Run migration
        migrate_database_for_cache_support()
        
        # Verify functionality
        verify_cache_functionality()
        
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("🎯 Enhanced flight search with caching is now ready!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        print("Please check the database and try again.")
