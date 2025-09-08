"""
Database Helper Functions for SerpAPI Project
Provides utilities for interacting with Main_DB.db
"""

import sqlite3
import json
import os
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any

# Track migrated databases to avoid repeated work per process
_MIGRATED: set[str] = set()

class SerpAPIDatabase:
    """Helper class for SerpAPI database operations"""
    
    def __init__(self, db_path: str = "Main_DB.db"):
        """Initialize database connection"""
        self.db_path = db_path
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("PRAGMA foreign_keys=ON")
        except Exception:
            pass
        # Automated migration: if legacy query_timestamp column still present, migrate
        self._ensure_migration(conn)
        # Ensure schema version manifest exists
        self._ensure_schema_version(conn)
        return conn

    def _ensure_migration(self, conn: sqlite3.Connection):
        """Drop legacy query_timestamp column from api_queries if still present.

        Safe / idempotent: No action if column already removed. Operates inside
        existing connection prior to usage. Minimal locking: per-process path cache.
        """
        path_key = os.path.abspath(self.db_path)
        if path_key in _MIGRATED:
            return
        cur = conn.cursor()
        try:
            cur.execute("PRAGMA table_info(api_queries)")
            cols = [r[1] for r in cur.fetchall()]
            if 'query_timestamp' not in cols:
                _MIGRATED.add(path_key)
                return
            # Perform in-place style migration (SQLite requires table rebuild)
            cur.execute("BEGIN TRANSACTION")
            cur.execute("""
                CREATE TABLE api_queries_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_parameters TEXT,
                    raw_response TEXT NOT NULL,
                    query_type TEXT,
                    status_code INTEGER,
                    response_size INTEGER,
                    api_endpoint TEXT,
                    search_term TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute(
                """INSERT INTO api_queries_new 
                    (id, query_parameters, raw_response, query_type, status_code, response_size, api_endpoint, search_term, created_at)
                    SELECT id, query_parameters, raw_response, query_type, status_code, response_size, api_endpoint, search_term, 
                           COALESCE(created_at, query_timestamp) FROM api_queries"""
            )
            cur.execute("DROP TABLE api_queries")
            cur.execute("ALTER TABLE api_queries_new RENAME TO api_queries")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON api_queries(created_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_query_type ON api_queries(query_type)")
            conn.commit()
            _MIGRATED.add(path_key)
            print("🔄 Automated migration: removed legacy query_timestamp column from api_queries")
        except Exception as e:
            conn.rollback()
            print(f"⚠️ Automated migration failed (continuing with legacy schema): {e}")
        finally:
            cur.close()

    def _ensure_schema_version(self, conn: sqlite3.Connection):
        """Create and initialize schema_version table if missing.

        Records baseline version post legacy column removal & observability P1.
        """
        cur = conn.cursor()
        try:
            cur.execute("CREATE TABLE IF NOT EXISTS schema_version (id INTEGER PRIMARY KEY CHECK(id=1), version TEXT NOT NULL, applied_at TEXT NOT NULL)")
            cur.execute("SELECT version FROM schema_version WHERE id=1")
            row = cur.fetchone()
            if not row:
                cur.execute("INSERT INTO schema_version (id, version, applied_at) VALUES (1, ?, ?)", ("2025.09.08-baseline", datetime.now().isoformat()))
                conn.commit()
        except Exception:
            pass
        finally:
            cur.close()

    def get_schema_version(self) -> Optional[str]:
        """Return current schema version string or None if unavailable."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("SELECT version FROM schema_version WHERE id=1")
            row = cur.fetchone()
            return row[0] if row else None
        except Exception:
            return None
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
    
    def insert_api_response(self, 
                          query_parameters: Dict[str, Any],
                          raw_response: str,
                          query_type: str = "search",
                          status_code: int = 200,
                          api_endpoint: str = "serpapi",
                          search_term: str = "") -> int:
        """
        Insert API response data into database
        
        Args:
            query_parameters: The parameters used for the API query
            raw_response: Complete raw response from API
            query_type: Type of query (search, images, news, etc.)
            status_code: HTTP status code
            api_endpoint: API endpoint used
            search_term: Search term used
            
        Returns:
            int: ID of inserted record
        """
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Prepare data
            # Post-migration: query_timestamp column removed; created_at default handles capture.
            query_params_json = json.dumps(query_parameters) if query_parameters else "{}"
            response_size = len(raw_response.encode('utf-8'))
            
            # Insert data
            cursor.execute('''
                INSERT INTO api_queries 
                (query_parameters, raw_response, query_type, status_code, response_size, api_endpoint, search_term)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (query_params_json, raw_response, query_type,
                  status_code, response_size, api_endpoint, search_term))
            
            record_id = cursor.lastrowid
            
            # Update metadata
            self._update_metadata(cursor)
            
            conn.commit()
            logging.getLogger(__name__).info(f"Inserted api_queries record id={record_id}")
            return record_id
            
        except sqlite3.Error as e:
            logging.getLogger(__name__).error(f"Error inserting API response: {e}")
            conn.rollback()
            raise
        
        finally:
            conn.close()
    
    def get_api_responses(self, 
                         query_type: Optional[str] = None,
                         search_term: Optional[str] = None,
                         limit: int = 100) -> List[Dict]:
        """
        Retrieve API responses from database
        
        Args:
            query_type: Filter by query type
            search_term: Filter by search term
            limit: Maximum number of records to return
            
        Returns:
            List[Dict]: List of API response records
        """
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Build query
            query = "SELECT * FROM api_queries WHERE 1=1"
            params = []
            
            if query_type:
                query += " AND query_type = ?"
                params.append(query_type)
            
            if search_term:
                query += " AND search_term LIKE ?"
                params.append(f"%{search_term}%")
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            # Get column names
            columns = [description[0] for description in cursor.description]
            
            # Fetch and format results
            rows = cursor.fetchall()
            results = []
            
            for row in rows:
                record = dict(zip(columns, row))
                # Parse JSON fields
                if record['query_parameters']:
                    try:
                        record['query_parameters'] = json.loads(record['query_parameters'])
                    except json.JSONDecodeError:
                        pass
                results.append(record)
            
            return results
            
        except sqlite3.Error as e:
            logging.getLogger(__name__).error(f"Error retrieving API responses: {e}")
            raise
        
        finally:
            conn.close()
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # Total records
            cursor.execute("SELECT COUNT(*) FROM api_queries")
            stats['total_records'] = cursor.fetchone()[0]
            
            # Records by type
            cursor.execute("""
                SELECT query_type, COUNT(*) 
                FROM api_queries 
                GROUP BY query_type
            """)
            stats['records_by_type'] = dict(cursor.fetchall())
            
            # Date range
            cursor.execute("""
                SELECT MIN(created_at), MAX(created_at) 
                FROM api_queries
            """)
            date_range = cursor.fetchone()
            stats['date_range'] = {
                'earliest': date_range[0],
                'latest': date_range[1]
            }
            
            # Database metadata
            cursor.execute("SELECT * FROM database_metadata WHERE id = 1")
            metadata = cursor.fetchone()
            if metadata:
                stats['metadata'] = {
                    'database_version': metadata[1],
                    'created_date': metadata[2],
                    'last_modified': metadata[3]
                }
            
            return stats
            
        except sqlite3.Error as e:
            logging.getLogger(__name__).error(f"Error getting database stats: {e}")
            raise
        
        finally:
            conn.close()
    
    def _update_metadata(self, cursor):
        """Update database metadata"""
        cursor.execute("""
            UPDATE database_metadata 
            SET last_modified = ?, 
                total_queries = (SELECT COUNT(*) FROM api_queries)
            WHERE id = 1
        """, (datetime.now().isoformat(),))

def test_database_operations():
    """Test database helper functions"""
    
    print("🧪 Testing database operations...")
    
    db = SerpAPIDatabase()
    
    # Test insert
    test_params = {
        "q": "test search",
        "engine": "google",
        "location": "United States"
    }
    
    test_response = json.dumps({
        "search_metadata": {"status": "Success"},
        "organic_results": [
            {"title": "Test Result", "link": "https://example.com"}
        ]
    })
    
    record_id = db.insert_api_response(
        query_parameters=test_params,
        raw_response=test_response,
        query_type="google_search",
        search_term="test search"
    )
    
    print(f"✅ Test record inserted with ID: {record_id}")
    
    # Test retrieve
    results = db.get_api_responses(limit=5)
    print(f"✅ Retrieved {len(results)} records")
    
    # Test stats
    stats = db.get_database_stats()
    print(f"✅ Database stats: {stats['total_records']} total records")
    
    print("🎉 Database operations test completed successfully!")

if __name__ == "__main__":
    test_database_operations()
