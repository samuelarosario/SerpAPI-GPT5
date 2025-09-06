"""
Database Schema Inspector and Deletion Script
"""
import sqlite3

def inspect_database_schema():
    """Inspect the complete database schema"""
    print("📋 CHECKING CURRENT DATABASE SCHEMA")
    print("=" * 40)
    
    with sqlite3.connect("Main_DB.db") as conn:
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"📊 Found {len(tables)} tables:")
        for table in tables:
            print(f"   - {table}")
        
        print("\n🔍 TABLE STRUCTURES AND RECORD COUNTS:")
        
        for table in tables:
            print(f"\n📋 {table.upper()}:")
            
            # Get table structure
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            
            for col in columns:
                col_name, col_type, not_null, default, pk = col[1], col[2], col[3], col[4], col[5]
                pk_marker = " (PK)" if pk else ""
                print(f"   {col_name} {col_type}{pk_marker}")
            
            # Get record count
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   → {count} records")
        
        print("\n🔗 CHECKING FOREIGN KEY RELATIONSHIPS:")
        
        for table in tables:
            cursor.execute(f"PRAGMA foreign_key_list({table})")
            fks = cursor.fetchall()
            if fks:
                print(f"\n{table}:")
                for fk in fks:
                    print(f"   {fk[3]} → {fk[2]}.{fk[4]}")
        
        return tables

def delete_all_records(tables):
    """Delete all records from all tables in correct order"""
    print("\n🗑️ DELETING ALL RECORDS")
    print("=" * 25)
    
    with sqlite3.connect("Main_DB.db") as conn:
        cursor = conn.cursor()
        
        # Disable foreign key constraints temporarily
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        print("📊 RECORDS BEFORE DELETION:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   {table}: {count}")
        
        print("\n🗑️ DELETING RECORDS...")
        
        # Delete from all tables
        for table in tables:
            cursor.execute(f"DELETE FROM {table}")
            print(f"   ✅ Cleared {table}")
        
        # Re-enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")
        
        conn.commit()
        
        print("\n📊 RECORDS AFTER DELETION:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   {table}: {count}")
        
        print("\n🎉 ALL RECORDS DELETED SUCCESSFULLY!")

if __name__ == "__main__":
    tables = inspect_database_schema()
    delete_all_records(tables)
