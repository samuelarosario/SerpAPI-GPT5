"""
Check airline code storage issue - looking for proper IATA codes
"""
import sqlite3
import json

def check_airline_codes():
    """Check what airline codes are actually stored and look for IATA codes"""
    print("🔍 CHECKING AIRLINE CODE STORAGE ISSUE")
    print("=" * 40)
    
    with sqlite3.connect("../DB/Main_DB.db") as conn:
        cursor = conn.cursor()
        
        # Check what's actually stored in airline_code fields
        print("📊 FLIGHT_SEGMENTS airline_code values:")
        cursor.execute("SELECT DISTINCT airline_code FROM flight_segments")
        airline_codes = cursor.fetchall()
        
        for code in airline_codes:
            print(f"   \"{code[0]}\"")
        
        print("\n📊 AIRLINES table data:")
        cursor.execute("SELECT airline_code, airline_name FROM airlines")
        airlines = cursor.fetchall()
        
        for airline in airlines:
            print(f"   Code: \"{airline[0]}\" -> Name: \"{airline[1]}\"")
        
        # Check if there are any JSON fields that might contain IATA codes
        print("\n🔍 CHECKING FOR IATA CODES IN JSON FIELDS:")
        
        # Check extensions field in flight_segments
        cursor.execute("SELECT extensions FROM flight_segments WHERE extensions IS NOT NULL LIMIT 3")
        extensions = cursor.fetchall()
        
        for ext in extensions:
            if ext[0]:
                try:
                    data = json.loads(ext[0])
                    print(f"   Extensions: {data}")
                except:
                    print(f"   Extensions (raw): {ext[0]}")
        
        # Check detailed flight segment data for more clues
        print("\n📋 DETAILED FLIGHT SEGMENT ANALYSIS:")
        cursor.execute("""
        SELECT airline_code, flight_number, extensions, plane_and_crew_by,
               ticket_also_sold_by
        FROM flight_segments 
        LIMIT 5
        """)
        
        segments = cursor.fetchall()
        for segment in segments:
            airline_code, flight_num, extensions, crew_by, sold_by = segment
            print(f"\n   Flight: {airline_code} {flight_num}")
            print(f"   Extensions: {extensions}")
            print(f"   Crew by: {crew_by}")
            print(f"   Sold by: {sold_by}")
        
        # Look for known airline IATA codes
        print("\n💡 AIRLINE IATA CODE ANALYSIS:")
        known_iata_codes = {
            "Philippine Airlines": "PR",
            "Air Niugini": "PX", 
            "Cathay Pacific": "CX",
            "Virgin Australia": "VA"
        }
        
        for airline_name, expected_iata in known_iata_codes.items():
            # Check if flight numbers contain the IATA code
            cursor.execute("""
            SELECT flight_number, airline_code 
            FROM flight_segments 
            WHERE airline_code = ? OR flight_number LIKE ?
            """, (airline_name, f"{expected_iata}%"))
            
            flights = cursor.fetchall()
            if flights:
                print(f"\n   {airline_name} (Expected IATA: {expected_iata}):")
                for flight in flights:
                    print(f"     Flight: {flight[0]}, Stored as: {flight[1]}")

if __name__ == "__main__":
    check_airline_codes()
