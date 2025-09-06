#!/usr/bin/env python3
"""
Debug Flight Search Storage
"""

import sys
import os
import sqlite3
from datetime import datetime

# Add the main directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Main'))

from enhanced_flight_search import EnhancedFlightSearchClient

def debug_flight_search():
    """Debug a flight search to see what's being stored"""
    print("🔍 DEBUG: Testing flight search storage...")
    
    # Clear any old test data first
    with sqlite3.connect('../DB/Main_DB.db') as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM flight_searches WHERE search_id LIKE 'test_%'")
        conn.commit()
    
    # Initialize the client
    client = EnhancedFlightSearchClient()
    
    # Test a simple flight search
    print("\n🔍 Performing test flight search...")
    result = client.search_flights(
        departure_id="LAX",
        arrival_id="JFK", 
        outbound_date="2025-12-20",
        return_date="2025-12-27"
    )
    
    print(f"\n📊 Search result:")
    print(f"  Success: {result.get('success')}")
    print(f"  Source: {result.get('source')}")
    print(f"  Search ID: {result.get('search_id')}")
    
    if result.get('data'):
        data = result['data']
        print(f"  Best flights: {len(data.get('best_flights', []))}")
        print(f"  Other flights: {len(data.get('other_flights', []))}")
        
        # Check one flight for airport data
        if data.get('best_flights'):
            flight = data['best_flights'][0]
            print(f"\n📋 Sample flight data:")
            flights = flight.get('flights', [])
            if flights:
                first_segment = flights[0]
                print(f"  Departure: {first_segment.get('departure_airport', {})}")
                print(f"  Arrival: {first_segment.get('arrival_airport', {})}")
                print(f"  Airline: {first_segment.get('airline')}")
    
    # Check database after search
    print("\n📊 Database status after search:")
    with sqlite3.connect('../DB/Main_DB.db') as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM flight_searches")
        searches = cursor.fetchone()[0]
        print(f"  Flight searches: {searches}")
        
        cursor.execute("SELECT COUNT(*) FROM flight_results")
        results = cursor.fetchone()[0]
        print(f"  Flight results: {results}")
        
        cursor.execute("SELECT COUNT(*) FROM flight_segments")
        segments = cursor.fetchone()[0]
        print(f"  Flight segments: {segments}")
        
        cursor.execute("SELECT COUNT(*) FROM airports")
        airports = cursor.fetchone()[0]
        print(f"  Airports: {airports}")
        
        cursor.execute("SELECT COUNT(*) FROM airlines")
        airlines = cursor.fetchone()[0]
        print(f"  Airlines: {airlines}")
        
        # Show latest search if any
        if searches > 0:
            cursor.execute("""
            SELECT search_id, departure_id, arrival_id, total_results 
            FROM flight_searches 
            WHERE search_id NOT LIKE 'test_%'
            ORDER BY created_at DESC LIMIT 1
            """)
            search = cursor.fetchone()
            if search:
                print(f"  Latest search: {search[0]} - {search[1]} → {search[2]} ({search[3]} results)")

if __name__ == "__main__":
    debug_flight_search()
