"""Database helper utilities for SerpAPI project (enhanced)."""

from __future__ import annotations

import sqlite3
import json
import os
import logging
import hashlib
from datetime import datetime
from typing import Optional, Dict, List, Any

_MIGRATED: set[str] = set()  # process-level cache of migrated db paths


class SerpAPIDatabase:
    """Encapsulates SQLite operations, migrations, and integrity utilities."""

    def __init__(self, db_path: str = "DB/Main_DB.db", enable_wal: bool = True) -> None:
        self.db_path = db_path
        self.enable_wal = enable_wal

    # ------------------------------------------------------------------
    # Connection / Bootstrap
    # ------------------------------------------------------------------
    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        try:
            if self.enable_wal:
                try:
                    conn.execute("PRAGMA journal_mode=WAL")
                except Exception:
                    pass
            conn.execute("PRAGMA foreign_keys=ON")
        except Exception:
            pass
        self._ensure_migration(conn)
        self._ensure_schema_version(conn)
        return conn

    # ------------------------------------------------------------------
    # Migration (legacy cleanup)
    # ------------------------------------------------------------------
    def _ensure_migration(self, conn: sqlite3.Connection) -> None:
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
            cur.execute("BEGIN TRANSACTION")
            cur.execute(
                """
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
                """
            )
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
        except Exception as e:  # pragma: no cover (rare path)
            conn.rollback()
            print(f"⚠️ Automated migration failed (continuing with legacy schema): {e}")
        finally:
            cur.close()

    # ------------------------------------------------------------------
    # Version / History
    # ------------------------------------------------------------------
    def _ensure_schema_version(self, conn: sqlite3.Connection) -> None:
        cur = conn.cursor()
        try:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS schema_version (id INTEGER PRIMARY KEY CHECK(id=1), version TEXT NOT NULL, applied_at TEXT NOT NULL)"
            )
            cur.execute("SELECT version FROM schema_version WHERE id=1")
            if not (row := cur.fetchone()):
                cur.execute(
                    "INSERT INTO schema_version (id, version, applied_at) VALUES (1, ?, ?)",
                    ("2025.09.08-baseline", datetime.now().isoformat()),
                )
                conn.commit()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS migration_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL,
                    applied_at TEXT NOT NULL,
                    description TEXT,
                    checksum TEXT
                )
                """
            )
            cur.execute("SELECT id, checksum FROM migration_history WHERE version=?", ("2025.09.08-baseline",))
            mh = cur.fetchone()
            if not mh:
                cur.execute(
                    "INSERT INTO migration_history (version, applied_at, description, checksum) VALUES (?,?,?,?)",
                    ("2025.09.08-baseline", datetime.now().isoformat(), "Baseline post legacy column removal", None),
                )
                conn.commit()
                cur.execute("SELECT id, checksum FROM migration_history WHERE version=?", ("2025.09.08-baseline",))
                mh = cur.fetchone()
            if mh and mh[1] is None:
                try:
                    checksum = self.compute_schema_checksum(conn)
                    cur.execute("UPDATE migration_history SET checksum=? WHERE id=?", (checksum, mh[0]))
                    conn.commit()
                except Exception:  # pragma: no cover
                    pass
        except Exception:  # pragma: no cover
            pass
        finally:
            cur.close()

    def get_schema_version(self) -> Optional[str]:
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("SELECT version FROM schema_version WHERE id=1")
            row = cur.fetchone()
            return row[0] if row else None
        except Exception:  # pragma: no cover
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

    # ------------------------------------------------------------------
    # Drift Detection
    # ------------------------------------------------------------------
    def detect_schema_drift(self, expected_tables: Optional[List[str]] = None) -> Dict[str, Any]:
        if expected_tables is None:
            expected_tables = [
                'airlines', 'airports', 'api_queries', 'schema_version', 'database_metadata',
                'flight_results', 'flight_searches', 'flight_segments', 'layovers', 'price_insights', 'route_analytics', 'migration_history'
            ]
        actual: List[str] = []
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            actual = sorted(r[0] for r in cur.fetchall())
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
        missing = [t for t in expected_tables if t not in actual]
        unexpected = [t for t in actual if t not in expected_tables]
        return {"missing": missing, "unexpected": unexpected, "ok": not missing}

    # ------------------------------------------------------------------
    # Integrity / Schema Utilities
    # ------------------------------------------------------------------
    def compute_schema_checksum(self, conn: Optional[sqlite3.Connection] = None) -> str:
        own = False
        if conn is None:
            conn = sqlite3.connect(self.db_path)
            own = True
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT name, sql FROM sqlite_master WHERE type IN ('table','index') AND name NOT LIKE 'sqlite_%'"
            )
            rows = [(r[0], r[1] or "") for r in cur.fetchall()]
            parts = [f"-- {name}\n{sql.strip()}" for name, sql in sorted(rows, key=lambda r: r[0])]
            canonical = "\n".join(parts)
            return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        finally:
            if own:
                try:
                    conn.close()
                except Exception:
                    pass

    def run_integrity_check(self) -> Dict[str, Any]:
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA quick_check")
            quick = [r[0] for r in cur.fetchall()]
            cur.execute("PRAGMA integrity_check")
            full = [r[0] for r in cur.fetchall()]
            return {"quick_check": quick, "integrity_check": full, "ok": quick == ['ok'] and full == ['ok']}
        finally:
            conn.close()

    def generate_schema_snapshot(self, output_path: Optional[str] = None) -> str:
        if output_path is None:
            base_dir = os.path.dirname(os.path.abspath(self.db_path)) or '.'
            if os.path.basename(base_dir).lower() != 'db':
                candidate = os.path.join(os.path.dirname(base_dir), 'DB')
                if os.path.isdir(candidate):
                    base_dir = candidate
            output_path = os.path.join(base_dir, 'current_schema.sql')
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT name, type, sql FROM sqlite_master WHERE type IN ('table','index') AND name NOT LIKE 'sqlite_%'"
            )
            rows = cur.fetchall()
            lines = ["-- Auto-generated schema snapshot", f"-- Generated: {datetime.now().isoformat()}"]
            table_names = [r[0] for r in rows if r[1] == 'table']
            lines.append(f"-- Tables: {len(table_names)}")
            lines.append(f"-- Table List: {', '.join(sorted(table_names))}")
            lines.append("")
            for name, typ, sql in sorted(rows, key=lambda r: (r[1], r[0])):
                lines.append(f"-- {typ.upper()}: {name}")
                if sql:
                    lines.append(sql.strip() + ";")
                lines.append("")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))
            checksum = self.compute_schema_checksum(conn)
            try:
                cur.execute(
                    "UPDATE migration_history SET checksum=? WHERE version=? AND (checksum IS NULL OR checksum='')",
                    (checksum, '2025.09.08-baseline'),
                )
                conn.commit()
            except Exception:  # pragma: no cover
                pass
            return checksum
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Data Operations (unchanged logic apart from connection bootstrap)
    # ------------------------------------------------------------------
    def insert_api_response(
        self,
        query_parameters: Dict[str, Any],
        raw_response: str,
        query_type: str = "search",
        status_code: int = 200,
        api_endpoint: str = "serpapi",
        search_term: str = "",
    ) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            query_params_json = json.dumps(query_parameters) if query_parameters else "{}"
            response_size = len(raw_response.encode("utf-8"))
            cursor.execute(
                """
                INSERT INTO api_queries
                (query_parameters, raw_response, query_type, status_code, response_size, api_endpoint, search_term)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query_params_json,
                    raw_response,
                    query_type,
                    status_code,
                    response_size,
                    api_endpoint,
                    search_term,
                ),
            )
            record_id = cursor.lastrowid
            self._update_metadata(cursor)
            conn.commit()
            logging.getLogger(__name__).info(f"Inserted api_queries record id={record_id}")
            return record_id
        except sqlite3.Error as e:  # pragma: no cover
            logging.getLogger(__name__).error(f"Error inserting API response: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_api_responses(
        self,
        query_type: Optional[str] = None,
        search_term: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            query = "SELECT * FROM api_queries WHERE 1=1"
            params: List[Any] = []
            if query_type:
                query += " AND query_type = ?"
                params.append(query_type)
            if search_term:
                query += " AND search_term LIKE ?"
                params.append(f"%{search_term}%")
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            cursor.execute(query, params)
            columns = [d[0] for d in cursor.description]
            results: List[Dict[str, Any]] = []
            for row in cursor.fetchall():
                record = dict(zip(columns, row))
                if record.get("query_parameters"):
                    try:
                        record["query_parameters"] = json.loads(record["query_parameters"])
                    except json.JSONDecodeError:  # pragma: no cover
                        pass
                results.append(record)
            return results
        except sqlite3.Error as e:  # pragma: no cover
            logging.getLogger(__name__).error(f"Error retrieving API responses: {e}")
            raise
        finally:
            conn.close()

    def get_database_stats(self) -> Dict[str, Any]:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            stats: Dict[str, Any] = {}
            cursor.execute("SELECT COUNT(*) FROM api_queries")
            stats["total_records"] = cursor.fetchone()[0]
            cursor.execute("SELECT query_type, COUNT(*) FROM api_queries GROUP BY query_type")
            stats["records_by_type"] = dict(cursor.fetchall())
            cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM api_queries")
            dr = cursor.fetchone()
            stats["date_range"] = {"earliest": dr[0], "latest": dr[1]}
            try:
                cursor.execute("SELECT * FROM database_metadata WHERE id = 1")
                metadata = cursor.fetchone()
                if metadata:
                    stats["metadata"] = {
                        "database_version": metadata[1],
                        "created_date": metadata[2],
                        "last_modified": metadata[3],
                    }
            except Exception:  # pragma: no cover
                pass
            return stats
        except sqlite3.Error as e:  # pragma: no cover
            logging.getLogger(__name__).error(f"Error getting database stats: {e}")
            raise
        finally:
            conn.close()

    def _update_metadata(self, cursor: sqlite3.Cursor) -> None:
        try:
            cursor.execute(
                """
                UPDATE database_metadata
                SET last_modified = ?,
                    total_queries = (SELECT COUNT(*) FROM api_queries)
                WHERE id = 1
                """,
                (datetime.now().isoformat(),),
            )
        except Exception:  # pragma: no cover
            pass


def test_database_operations():  # pragma: no cover - retained from original for manual smoke
    print("🧪 Testing database operations...")
    db = SerpAPIDatabase()
    test_params = {"q": "test search", "engine": "google", "location": "United States"}
    test_response = json.dumps({
        "search_metadata": {"status": "Success"},
        "organic_results": [{"title": "Test Result", "link": "https://example.com"}]
    })
    record_id = db.insert_api_response(
        query_parameters=test_params,
        raw_response=test_response,
        query_type="google_search",
        search_term="test search",
    )
    print(f"✅ Test record inserted with ID: {record_id}")
    results = db.get_api_responses(limit=5)
    print(f"✅ Retrieved {len(results)} records")
    stats = db.get_database_stats()
    print(f"✅ Database stats: {stats['total_records']} total records")
    print("🎉 Database operations test completed successfully!")


if __name__ == "__main__":  # pragma: no cover
    test_database_operations()
    
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
