#!/usr/bin/env python3
"""
Apply Enhanced Schema to flight_data.db
"""

import sqlite3

def apply_enhanced_schema():
    """Apply enhanced schema to flight_data.db"""
    
    # Read current schema (SCHEMA CHANGES RESTRICTED - REQUIRES EXPLICIT APPROVAL)
    with open('../DB/current_schema.sql', 'r') as f:
        schema_sql = f.read()
    
    # Apply to flight_data.db
    conn = sqlite3.connect('flight_data.db')
    cursor = conn.cursor()
    
    print('📊 Applying enhanced schema to flight_data.db...')
    cursor.executescript(schema_sql)
    conn.commit()
    
    # Check tables
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f'✅ Tables now available ({len(tables)}): {tables}')
    
    print('✅ Airports table exists:', 'airports' in tables)
    print('✅ Airlines table exists:', 'airlines' in tables)
    
    conn.close()
    return 'airports' in tables and 'airlines' in tables

if __name__ == "__main__":
    success = apply_enhanced_schema()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Schema application {'completed' if success else 'failed'}")
