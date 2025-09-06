"""
Simple Database Checker
"""
import sqlite3
import os

print("🔍 CHECKING DATABASE FILES")
print("=" * 30)

# Check current directory
print(f"Current directory: {os.getcwd()}")

# List all .db files
db_files = [f for f in os.listdir('.') if f.endswith('.db')]
print(f"Database files found: {db_files}")

# Check Main_DB.db specifically
if os.path.exists("Main_DB.db"):
    print("\n✅ Main_DB.db found!")
    
    with sqlite3.connect("Main_DB.db") as conn:
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"Tables: {len(tables)}")
        
        if tables:
            print("\n📊 TABLE RECORD COUNTS:")
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"   {table_name}: {count} records")
        else:
            print("No tables found!")
else:
    print("❌ Main_DB.db not found!")
    print("Available files:", os.listdir('.'))
