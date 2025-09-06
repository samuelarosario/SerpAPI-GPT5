"""
Database Check Script
====================
"""
import sqlite3
import os

# Navigate to DB directory
db_path = "C:\\Users\\MY PC\\SerpAPI\\DB\\Main_DB.db"

if os.path.exists(db_path):
    print(f"✅ Database found: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"📊 Tables: {[t[0] for t in tables]}")
    
    # Check flights table
    try:
        cursor.execute("SELECT COUNT(*) FROM flights")
        flight_count = cursor.fetchone()[0]
        print(f"🛫 Flights records: {flight_count}")
        
        # Check recent records
        cursor.execute("SELECT search_id, departure_id, arrival_id, outbound_date FROM flights ORDER BY search_timestamp DESC LIMIT 5")
        recent = cursor.fetchall()
        print(f"📋 Recent searches:")
        for r in recent:
            print(f"   {r[0]} - {r[1]} → {r[2]} on {r[3]}")
            
    except Exception as e:
        print(f"❌ Error checking flights: {e}")
    
    # Check search_cache table
    try:
        cursor.execute("SELECT COUNT(*) FROM search_cache")
        cache_count = cursor.fetchone()[0]
        print(f"🗄️  Cache records: {cache_count}")
        
        if cache_count > 0:
            cursor.execute("SELECT search_id, cache_timestamp FROM search_cache ORDER BY cache_timestamp DESC LIMIT 3")
            cache_recent = cursor.fetchall()
            print(f"📋 Recent cache entries:")
            for c in cache_recent:
                print(f"   {c[0]} - {c[1]}")
                
    except Exception as e:
        print(f"❌ Error checking cache: {e}")
    
    conn.close()
    
else:
    print(f"❌ Database not found: {db_path}")
