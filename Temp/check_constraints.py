"""
Check table constraints and fix schema alignment
"""
import sqlite3

def check_table_constraints():
    """Check primary key constraints in reference tables"""
    print("🔍 CHECKING PRIMARY KEY CONSTRAINTS")
    print("=" * 37)
    
    with sqlite3.connect("../DB/Main_DB.db") as conn:
        cursor = conn.cursor()
        
        # Check airports table
        print("AIRPORTS TABLE:")
        cursor.execute("PRAGMA table_info(airports)")
        for col in cursor.fetchall():
            if col[5]:  # If primary key
                print(f"   PRIMARY KEY: {col[1]}")
        
        cursor.execute("SELECT sql FROM sqlite_master WHERE name='airports'")
        create_sql = cursor.fetchone()[0]
        print(f"   Creation SQL: {create_sql}")
        
        print("\nAIRLINES TABLE:")
        cursor.execute("PRAGMA table_info(airlines)")
        for col in cursor.fetchall():
            if col[5]:  # If primary key
                print(f"   PRIMARY KEY: {col[1]}")
        
        cursor.execute("SELECT sql FROM sqlite_master WHERE name='airlines'")
        create_sql = cursor.fetchone()[0]
        print(f"   Creation SQL: {create_sql}")
        
        print("\n🔗 CHECKING UNIQUE CONSTRAINTS:")
        
        # Check if airport_code and airline_code have unique constraints
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='index'")
        indexes = cursor.fetchall()
        
        for index in indexes:
            if index[0] and ('airport' in index[0] or 'airline' in index[0]):
                print(f"   Index: {index[0]}")

if __name__ == "__main__":
    check_table_constraints()
