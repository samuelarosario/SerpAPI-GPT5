#!/usr/bin/env python3
"""
Debug the POM → CDG flight search to see what actually happened
"""

import sys
sys.path.append('Main')
sys.path.append('DB')
from enhanced_flight_search import EnhancedFlightSearchClient
from database_helper import SerpAPIDatabase

def debug_pom_cdg_search():
    """Debug the recent POM → CDG search to see what went wrong"""
    
    print('🔍 Debugging POM → CDG Flight Search Results')
    print('=' * 50)
    
    # Check database for the recent search
    db = SerpAPIDatabase('DB/Main_DB.db')
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Look for recent POM → CDG searches
        cursor.execute("""
            SELECT search_id, departure_airport_code, arrival_airport_code, 
                   outbound_date, response_status, total_results, created_at,
                   raw_parameters
            FROM flight_searches 
            WHERE departure_airport_code = 'POM' AND arrival_airport_code = 'CDG'
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        recent_search = cursor.fetchone()
        
        if recent_search:
            print(f"📋 Found Recent Search:")
            print(f"   Search ID: {recent_search[0]}")
            print(f"   Route: {recent_search[1]} → {recent_search[2]}")
            print(f"   Date: {recent_search[3]}")
            print(f"   Status: {recent_search[4]}")
            print(f"   Results: {recent_search[5]}")
            print(f"   Time: {recent_search[6]}")
            print()
            
            # Check the raw API response
            cursor.execute("""
                SELECT raw_response, status_code, response_size
                FROM api_queries 
                WHERE search_term LIKE '%POM%CDG%' OR search_term LIKE '%cdg%'
                ORDER BY created_at DESC 
                LIMIT 1
            """)
            
            api_response = cursor.fetchone()
            
            if api_response:
                print(f"📡 API Response Details:")
                print(f"   Status Code: {api_response[1]}")
                print(f"   Response Size: {api_response[2]} bytes")
                print()
                
                # Parse the response to see what Google Flights returned
                import json
                try:
                    response_data = json.loads(api_response[0])
                    
                    # Check search metadata
                    if 'search_metadata' in response_data:
                        metadata = response_data['search_metadata']
                        print(f"🔧 Search Metadata:")
                        print(f"   Status: {metadata.get('status', 'N/A')}")
                        print(f"   Request ID: {metadata.get('id', 'N/A')}")
                        print(f"   Engine: {metadata.get('engine', 'N/A')}")
                        print()
                    
                    # Check if we have flights data
                    if 'best_flights' in response_data:
                        best_flights = response_data['best_flights']
                        print(f"✈️ Best Flights Found: {len(best_flights)}")
                        
                        for i, flight in enumerate(best_flights[:3], 1):
                            price = flight.get('price', 'N/A')
                            duration = flight.get('total_duration', 'N/A')
                            print(f"   {i}. {price} - {duration} minutes")
                    
                    if 'other_flights' in response_data:
                        other_flights = response_data['other_flights']
                        print(f"🛫 Other Flights Found: {len(other_flights)}")
                    
                    # Check for any error messages
                    if 'error' in response_data:
                        print(f"❌ API Error: {response_data['error']}")
                    
                    # Check search parameters that were actually sent
                    if 'search_parameters' in response_data:
                        params = response_data['search_parameters']
                        print(f"📝 Actual Search Parameters:")
                        print(f"   Engine: {params.get('engine', 'N/A')}")
                        print(f"   Departure: {params.get('departure_id', 'N/A')}")
                        print(f"   Arrival: {params.get('arrival_id', 'N/A')}")
                        print(f"   Date: {params.get('outbound_date', 'N/A')}")
                        print(f"   Adults: {params.get('adults', 'N/A')}")
                    
                except json.JSONDecodeError as e:
                    print(f"❌ Could not parse API response: {e}")
                    print(f"Raw response preview: {api_response[0][:200]}...")
            
            else:
                print("⚠️ No API response found in database")
        
        else:
            print("⚠️ No POM → CDG searches found in database")
            
            # Check if there are any recent searches at all
            cursor.execute("""
                SELECT search_id, departure_airport_code, arrival_airport_code, 
                       outbound_date, created_at
                FROM flight_searches 
                ORDER BY created_at DESC 
                LIMIT 3
            """)
            
            recent_searches = cursor.fetchall()
            print(f"\n📋 Recent Searches (any route):")
            for search in recent_searches:
                print(f"   {search[1]} → {search[2]} on {search[3]} at {search[4]}")
        
    except Exception as e:
        print(f"❌ Debug error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    debug_pom_cdg_search()
