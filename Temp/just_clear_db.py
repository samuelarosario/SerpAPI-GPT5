"""
Just clear the database - no API calls
"""
import sys
import os

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Main'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'DB'))

from enhanced_flight_search import FlightSearchCache

def clear_database_only():
    """Clear database records only - no API calls"""
    
    print("🗑️ CLEARING DATABASE RECORDS ONLY")
    print("=" * 35)
    
    # Use the cache system to clear data properly
    cache = FlightSearchCache("../DB/Main_DB.db")
    
    print("🧹 Clearing all cached data...")
    try:
        # Use cleanup method with 0 hours to delete everything older than 0 hours (everything)
        cache.cleanup_old_data(max_age_hours=0)
        print("✅ Database cleanup completed")
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
    
    # Verify the cleanup worked
    print("\n📊 Verifying database is clear...")
    
    import sqlite3
    with sqlite3.connect("../DB/Main_DB.db") as conn:
        cursor = conn.cursor()
        
        # Check key tables
        tables_to_check = ['flight_searches', 'flight_results', 'flight_segments', 'layovers', 'airports', 'airlines']
        
        total_records = 0
        for table in tables_to_check:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                total_records += count
                print(f"   {table}: {count} records")
            except:
                print(f"   {table}: table not found")
        
        print(f"\nTotal records remaining: {total_records}")
        
        if total_records == 0:
            print("🎉 DATABASE IS COMPLETELY CLEAR!")
        else:
            print(f"⚠️  {total_records} records still remain")

if __name__ == "__main__":
    clear_database_only()
