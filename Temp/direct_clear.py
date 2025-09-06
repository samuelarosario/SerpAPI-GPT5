"""
Direct database clearing - no dependencies
"""
import sqlite3
import time

def clear_database_directly():
    """Clear database records directly using SQL"""
    
    print("🗑️ DIRECT DATABASE CLEARING")
    print("=" * 30)
    
    db_path = "../DB/Main_DB.db"
    
    # Try multiple times with increasing timeout
    for attempt in range(3):
        try:
            print(f"Attempt {attempt + 1}/3...")
            
            with sqlite3.connect(db_path, timeout=30) as conn:
                cursor = conn.cursor()
                
                # First, check current record counts
                tables = ['flight_searches', 'flight_results', 'flight_segments', 'layovers', 'airports', 'airlines', 'price_insights', 'api_queries']
                
                print("📊 Records before deletion:")
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        print(f"   {table}: {count}")
                    except sqlite3.OperationalError:
                        print(f"   {table}: table not found")
                
                print("\n🗑️ Deleting records...")
                
                # Disable foreign key constraints temporarily
                cursor.execute("PRAGMA foreign_keys = OFF")
                
                # Delete in safe order
                deletion_order = [
                    'layovers',
                    'flight_segments', 
                    'flight_results',
                    'price_insights',
                    'flight_searches',
                    'api_queries',
                    'airports',
                    'airlines'
                ]
                
                for table in deletion_order:
                    try:
                        cursor.execute(f"DELETE FROM {table}")
                        print(f"   ✅ Cleared {table}")
                    except sqlite3.OperationalError as e:
                        print(f"   ⚠️  {table}: {e}")
                
                # Reset auto-increment sequences
                cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('flight_searches', 'flight_results', 'flight_segments', 'layovers', 'airports', 'airlines')")
                
                # Re-enable foreign key constraints
                cursor.execute("PRAGMA foreign_keys = ON")
                
                conn.commit()
                
                print("\n📊 Records after deletion:")
                total_remaining = 0
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        total_remaining += count
                        print(f"   {table}: {count}")
                    except sqlite3.OperationalError:
                        print(f"   {table}: table not found")
                
                if total_remaining == 0:
                    print("\n🎉 DATABASE IS NOW COMPLETELY CLEAR!")
                    return True
                else:
                    print(f"\n⚠️  {total_remaining} records still remain")
                    return False
                    
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                print(f"   Database locked, waiting {2 * (attempt + 1)} seconds...")
                time.sleep(2 * (attempt + 1))
            else:
                print(f"   Error: {e}")
                return False
    
    print("❌ Failed to clear database after 3 attempts")
    return False

if __name__ == "__main__":
    success = clear_database_directly()
    if success:
        print("\n✅ Ready for fresh POM → MNL search!")
    else:
        print("\n❌ Database clearing incomplete")
