"""
Database Schema Upgrade Script for SerpAPI Flight Data
Applies enhanced schema while preserving existing data
"""

import sqlite3
import os
from datetime import datetime

def upgrade_database(db_path="Main_DB.db"):
    """
    Upgrade existing database with enhanced flight schema
    Preserves all existing data in api_queries table
    """
    
    print("🔄 Starting database schema upgrade...")
    
    # Backup existing database
    backup_path = f"Main_DB_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    try:
        # Create backup
        if os.path.exists(db_path):
            import shutil
            shutil.copy2(db_path, backup_path)
            print(f"✅ Database backup created: {backup_path}")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Read current schema
        with open("current_schema.sql", "r") as f:
            schema_sql = f.read()
        
        # Execute schema upgrade
        print("📊 Applying enhanced schema...")
        cursor.executescript(schema_sql)
        
        # Verify new tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            'flight_searches', 'flight_results', 'flight_segments', 
            'layovers', 'airlines', 'airports', 'price_insights', 
            'route_analytics'
        ]
        
        created_tables = [table for table in expected_tables if table in tables]
        
        print(f"✅ Created {len(created_tables)} new tables:")
        for table in created_tables:
            print(f"   - {table}")
        
        # Update database metadata
        cursor.execute("""
            UPDATE database_metadata 
            SET database_version = '2.0',
                last_modified = ?
            WHERE id = 1
        """, (datetime.now().isoformat(),))
        
        # Insert schema upgrade record
        cursor.execute("""
            INSERT INTO api_queries 
            (query_timestamp, query_parameters, raw_response, query_type, 
             status_code, response_size, api_endpoint, search_term)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            '{"upgrade": "enhanced_flight_schema"}',
            '{"status": "success", "tables_created": ' + str(len(created_tables)) + '}',
            'schema_upgrade',
            200,
            len(str(created_tables)),
            'database_upgrade',
            'enhanced_flight_schema_v2'
        ))
        
        conn.commit()
        
        # Get final database stats
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
        total_tables = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM api_queries")
        total_records = cursor.fetchone()[0]
        
        print(f"📈 Database upgrade completed successfully!")
        print(f"   - Total tables: {total_tables}")
        print(f"   - Total API records: {total_records}")
        print(f"   - Database version: 2.0")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during database upgrade: {e}")
        
        # Restore backup if upgrade failed
        if os.path.exists(backup_path):
            if os.path.exists(db_path):
                os.remove(db_path)
            os.rename(backup_path, db_path)
            print(f"🔄 Database restored from backup")
        
        return False
    
    finally:
        if conn:
            conn.close()

def test_enhanced_schema():
    """Test the enhanced schema functionality"""
    
    print("🧪 Testing enhanced schema...")
    
    try:
        conn = sqlite3.connect("Main_DB.db")
        cursor = conn.cursor()
        
        # Test flight_searches table
        test_search_data = (
            'test_search_001',
            datetime.now().isoformat(),
            'LAX',
            'JFK',
            '2025-09-10',
            '2025-09-17',
            1,  # Round trip
            2,  # Adults
            1,  # Children
            0, 0,  # Infants
            1,  # Economy
            'USD',
            'us',
            'en',
            1000,  # Max price
            0,  # Any stops
            False, False,  # Deep search, show hidden
            '{"test": "enhanced_schema"}',
            'Success',
            5  # Total results
        )
        
        cursor.execute("""
            INSERT INTO flight_searches 
            (search_id, search_timestamp, departure_id, arrival_id, outbound_date, 
             return_date, flight_type, adults, children, infants_in_seat, infants_on_lap,
             travel_class, currency, country_code, language_code, max_price, stops,
             deep_search, show_hidden, raw_parameters, response_status, total_results)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, test_search_data)
        
        # Test airlines table
        cursor.execute("""
            INSERT OR IGNORE INTO airlines 
            (airline_code, airline_name, alliance)
            VALUES 
            ('AA', 'American Airlines', 'ONEWORLD'),
            ('UA', 'United Airlines', 'STAR_ALLIANCE'),
            ('DL', 'Delta Air Lines', 'SKYTEAM')
        """)
        
        conn.commit()
        
        # Verify data insertion
        cursor.execute("SELECT COUNT(*) FROM flight_searches")
        search_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM airlines")
        airline_count = cursor.fetchone()[0]
        
        print(f"✅ Schema test completed:")
        print(f"   - Flight searches: {search_count}")
        print(f"   - Airlines: {airline_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Schema test failed: {e}")
        return False
    
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 Enhanced Database Schema Upgrade")
    print("=" * 50)
    
    if upgrade_database():
        if test_enhanced_schema():
            print("=" * 50)
            print("✅ Enhanced schema upgrade completed successfully!")
            print("🎯 Ready for advanced flight data processing")
        else:
            print("⚠️ Schema upgrade completed but test failed")
    else:
        print("❌ Schema upgrade failed")
