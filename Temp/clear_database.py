"""
Complete Database Cleanup Script
Based on actual schema inspection
"""
import sqlite3
import os

def clear_database():
    """Clear all records from the database"""
    print("🗑️ CLEARING ALL DATABASE RECORDS")
    print("=" * 40)
    
    db_path = "../DB/Main_DB.db"
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Get all tables (excluding system tables)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print("📊 CURRENT RECORD COUNTS:")
        total_before = 0
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            total_before += count
            print(f"   {table}: {count} records")
        
        print(f"\nTotal records before: {total_before}")
        
        if total_before == 0:
            print("✅ Database is already empty!")
            return
        
        print("\n🗑️ DELETING ALL RECORDS...")
        
        # Disable foreign key constraints temporarily
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        # Delete records from tables in safe order (children first)
        # Based on the foreign key relationships we discovered
        deletion_order = [
            'layovers',           # References flight_results
            'flight_segments',    # References flight_results, airports, airlines
            'flight_results',     # References flight_searches
            'price_insights',     # References flight_searches
            'flight_searches',    # Main search table
            'api_queries',        # Independent
            'airports',           # Referenced by flight_segments
            'airlines',           # Referenced by flight_segments
            'route_analytics',    # Analytics table
            'database_metadata'   # Metadata table
        ]
        
        deleted_count = 0
        for table in deletion_order:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                
                cursor.execute(f"DELETE FROM {table}")
                deleted_count += count
                print(f"   ✅ Cleared {table} ({count} records)")
        
        # Also clear sqlite_sequence (auto-increment tracking)
        cursor.execute("DELETE FROM sqlite_sequence")
        print("   ✅ Reset auto-increment sequences")
        
        # Re-enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")
        
        conn.commit()
        
        print(f"\n📊 VERIFICATION - RECORDS AFTER DELETION:")
        total_after = 0
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            total_after += count
            print(f"   {table}: {count} records")
        
        print(f"\nTotal records after: {total_after}")
        print(f"Records deleted: {deleted_count}")
        
        if total_after == 0:
            print("\n🎉 DATABASE SUCCESSFULLY CLEARED!")
            print("Ready for fresh POM → MNL search")
        else:
            print(f"\n⚠️  Warning: {total_after} records remaining")

if __name__ == "__main__":
    clear_database()
