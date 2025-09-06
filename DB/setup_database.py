"""
SQLite Database Setup Script for SerpAPI Project
Creates Main_DB.db with initial schema for storing API query data
"""

import sqlite3
import os
from datetime import datetime

def create_database():
    """Create the Main_DB SQLite database with initial schema"""
    
    # Database file path
    db_path = "Main_DB.db"
    
    print(f"Creating SQLite database: {db_path}")
    
    try:
        # Connect to SQLite database (creates file if it doesn't exist)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create main table for storing API query data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_timestamp TEXT NOT NULL,
                query_parameters TEXT,
                raw_response TEXT NOT NULL,
                query_type TEXT,
                status_code INTEGER,
                response_size INTEGER,
                api_endpoint TEXT,
                search_term TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_query_timestamp 
            ON api_queries(query_timestamp)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_created_at 
            ON api_queries(created_at)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_query_type 
            ON api_queries(query_type)
        ''')
        
        # Create metadata table for database information
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS database_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                database_version TEXT,
                created_date TEXT,
                last_modified TEXT,
                total_queries INTEGER DEFAULT 0
            )
        ''')
        
        # Insert initial metadata
        cursor.execute('''
            INSERT OR IGNORE INTO database_metadata 
            (id, database_version, created_date, last_modified, total_queries)
            VALUES (1, '1.0', ?, ?, 0)
        ''', (datetime.now().isoformat(), datetime.now().isoformat()))
        
        # Commit changes
        conn.commit()
        
        print("✅ Database created successfully!")
        print("📊 Tables created:")
        print("   - api_queries (main data storage)")
        print("   - database_metadata (tracking info)")
        print("🔍 Indexes created for optimized queries")
        
        # Verify tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"📋 Database contains {len(tables)} tables: {[table[0] for table in tables]}")
        
        # Get database info
        cursor.execute("PRAGMA database_list;")
        db_info = cursor.fetchall()
        print(f"💾 Database file: {os.path.abspath(db_path)}")
        print(f"📏 Database size: {os.path.getsize(db_path)} bytes")
        
    except sqlite3.Error as e:
        print(f"❌ Error creating database: {e}")
        return False
    
    finally:
        if conn:
            conn.close()
    
    return True

def test_database():
    """Test database connectivity and basic operations"""
    
    try:
        conn = sqlite3.connect("Main_DB.db")
        cursor = conn.cursor()
        
        # Test insert
        test_data = (
            datetime.now().isoformat(),
            '{"test": "initial_setup"}',
            '{"status": "database_created", "message": "Initial setup complete"}',
            'setup_test',
            200,
            100,
            'setup',
            'database_initialization'
        )
        
        cursor.execute('''
            INSERT INTO api_queries 
            (query_timestamp, query_parameters, raw_response, query_type, 
             status_code, response_size, api_endpoint, search_term)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', test_data)
        
        # Test select
        cursor.execute("SELECT COUNT(*) FROM api_queries")
        count = cursor.fetchone()[0]
        
        conn.commit()
        print(f"🧪 Database test successful! Records count: {count}")
        
    except sqlite3.Error as e:
        print(f"❌ Database test failed: {e}")
        return False
    
    finally:
        if conn:
            conn.close()
    
    return True

if __name__ == "__main__":
    print("🚀 Starting SQLite Database Setup...")
    print("=" * 50)
    
    if create_database():
        if test_database():
            print("=" * 50)
            print("✅ Main_DB SQLite database setup completed successfully!")
            print("📁 Location: /DB/Main_DB.db")
            print("🔧 Ready for SerpAPI data storage")
        else:
            print("⚠️ Database created but test failed")
    else:
        print("❌ Database setup failed")
