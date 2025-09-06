"""
Detailed Database Analysis
=========================
"""
import sqlite3
import os

# Database path
db_path = "C:\\Users\\MY PC\\SerpAPI\\DB\\Main_DB.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("🔍 DETAILED DATABASE ANALYSIS")
print("=" * 50)

# Get all tables with their column info
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

for table_name in [t[0] for t in tables]:
    print(f"\n📊 TABLE: {table_name}")
    print("-" * 30)
    
    # Get table schema
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    print("Columns:")
    for col in columns:
        print(f"   {col[1]} ({col[2]})")
    
    # Get record count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"Records: {count}")
    
    # Show sample data for tables with records
    if count > 0 and count <= 10:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
        sample = cursor.fetchall()
        print("Sample data:")
        for row in sample:
            print(f"   {row}")

print("\n" + "=" * 50)
print("🔍 LOOKING FOR FLIGHT DATA...")

# Check flight_searches table specifically
try:
    cursor.execute("SELECT COUNT(*) FROM flight_searches")
    fs_count = cursor.fetchone()[0]
    print(f"flight_searches records: {fs_count}")
    
    if fs_count > 0:
        cursor.execute("SELECT search_id, departure_id, arrival_id, outbound_date FROM flight_searches ORDER BY search_timestamp DESC LIMIT 5")
        recent = cursor.fetchall()
        print("Recent flight searches:")
        for r in recent:
            print(f"   {r}")
except Exception as e:
    print(f"Error with flight_searches: {e}")

# Check flight_results table
try:
    cursor.execute("SELECT COUNT(*) FROM flight_results")
    fr_count = cursor.fetchone()[0]
    print(f"flight_results records: {fr_count}")
    
    if fr_count > 0:
        cursor.execute("SELECT search_id, price, airline FROM flight_results LIMIT 5")
        results = cursor.fetchall()
        print("Recent flight results:")
        for r in results:
            print(f"   {r}")
except Exception as e:
    print(f"Error with flight_results: {e}")

conn.close()
