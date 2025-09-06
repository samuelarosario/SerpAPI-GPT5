"""
Flight Data Processor
Processes SerpAPI responses and stores structured data in database
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import os
import sys

# Add DB directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'DB'))

try:
    from database_helper import SerpAPIDatabase
except ImportError:
    # Fallback if import fails
    class SerpAPIDatabase:
        def __init__(self, db_path):
            self.db_path = db_path
        def insert_api_response(self, **kwargs):
            return 1  # Mock return for testing

class FlightDataProcessor:
    """Processes flight search results and stores in database"""
    
    def __init__(self, db_path: str = "../DB/Main_DB.db"):
        """Initialize the processor"""
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self.serpapi_db = SerpAPIDatabase(db_path)
    
    def process_search_response(self, search_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process complete search response and store all data
        
        Args:
            search_result: Complete response from SerpAPI client
            
        Returns:
            Dict with processing results and statistics
        """
        
        try:
            search_id = search_result['search_id']
            raw_response = search_result['raw_response']
            search_params = search_result['search_parameters']
            
            # Store raw API data first (maintains existing requirement)
            api_record_id = self._store_raw_api_data(search_result)
            
            # Process structured data if response is valid
            processing_stats = {
                'search_id': search_id,
                'api_record_id': api_record_id,
                'flights_processed': 0,
                'airlines_extracted': 0,
                'errors': []
            }
            
            if raw_response and 'search_metadata' in raw_response:
                # Store flight search record
                self._store_flight_search(search_id, search_params, raw_response, api_record_id)
                
                # Process flight results
                flights_stats = self._process_flight_results(search_id, raw_response)
                processing_stats.update(flights_stats)
                
                # Extract and store airlines
                airline_count = self._extract_airlines(raw_response)
                processing_stats['airlines_extracted'] = airline_count
                
                # Store price insights
                self._store_price_insights(search_id, raw_response)
                
                # Update route analytics
                self._update_route_analytics(search_params, raw_response)
                
            self.logger.info(f"Successfully processed search {search_id}")
            return processing_stats
            
        except Exception as e:
            self.logger.error(f"Error processing search response: {e}")
            processing_stats['errors'].append(str(e))
            return processing_stats
    
    def _store_raw_api_data(self, search_result: Dict[str, Any]) -> int:
        """Store raw API data using existing database helper"""
        
        query_params = search_result['search_parameters']
        raw_response = json.dumps(search_result['raw_response']) if search_result['raw_response'] else "{}"
        
        # Determine search term
        search_term = f"{query_params.get('departure_id', '')}-{query_params.get('arrival_id', '')}"
        
        return self.serpapi_db.insert_api_response(
            query_parameters=query_params,
            raw_response=raw_response,
            query_type="google_flights",
            status_code=200 if search_result['status'] == 'success' else 500,
            api_endpoint="google_flights",
            search_term=search_term
        )
    
    def _store_flight_search(self, search_id: str, params: Dict[str, Any], 
                           response: Dict[str, Any], api_record_id: int):
        """Store flight search record"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Count total results
            total_results = 0
            if 'best_flights' in response:
                total_results += len(response['best_flights'])
            if 'other_flights' in response:
                total_results += len(response['other_flights'])
            
            # Extract search parameters
            search_data = (
                search_id,
                datetime.now().isoformat(),
                params.get('departure_id'),
                params.get('arrival_id'),
                params.get('outbound_date'),
                params.get('return_date'),
                params.get('type', 1),
                params.get('adults', 1),
                params.get('children', 0),
                params.get('infants_in_seat', 0),
                params.get('infants_on_lap', 0),
                params.get('travel_class', 1),
                params.get('currency', 'USD'),
                params.get('gl', 'us'),
                params.get('hl', 'en'),
                params.get('max_price'),
                params.get('stops'),
                params.get('deep_search', False),
                params.get('show_hidden', False),
                json.dumps(params),
                response.get('search_metadata', {}).get('status', 'Unknown'),
                total_results,
                api_record_id
            )
            
            cursor.execute("""
                INSERT INTO flight_searches 
                (search_id, search_timestamp, departure_id, arrival_id, outbound_date, 
                 return_date, flight_type, adults, children, infants_in_seat, infants_on_lap,
                 travel_class, currency, country_code, language_code, max_price, stops,
                 deep_search, show_hidden, raw_parameters, response_status, total_results, api_query_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, search_data)
            
            conn.commit()
            
        finally:
            conn.close()
    
    def _process_flight_results(self, search_id: str, response: Dict[str, Any]) -> Dict[str, int]:
        """Process flight results and store in database"""
        
        flights_processed = 0
        
        # Process best flights
        if 'best_flights' in response:
            for rank, flight in enumerate(response['best_flights'], 1):
                self._store_flight_result(search_id, flight, 'best_flight', rank)
                flights_processed += 1
        
        # Process other flights
        if 'other_flights' in response:
            for rank, flight in enumerate(response['other_flights'], 1):
                self._store_flight_result(search_id, flight, 'other_flight', rank)
                flights_processed += 1
        
        return {'flights_processed': flights_processed}
    
    def _store_flight_result(self, search_id: str, flight_data: Dict[str, Any], 
                           result_type: str, rank: int):
        """Store individual flight result"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Extract flight result data
            carbon_emissions = flight_data.get('carbon_emissions', {})
            
            flight_result_data = (
                search_id,
                result_type,
                rank,
                flight_data.get('total_duration'),
                flight_data.get('price'),
                flight_data.get('currency', 'USD'),
                flight_data.get('type'),
                len(flight_data.get('layovers', [])),
                carbon_emissions.get('this_flight'),
                carbon_emissions.get('typical_for_this_route'),
                carbon_emissions.get('difference_percent'),
                flight_data.get('departure_token'),
                flight_data.get('booking_token'),
                flight_data.get('airline_logo')
            )
            
            cursor.execute("""
                INSERT INTO flight_results 
                (search_id, result_type, result_rank, total_duration, total_price, 
                 price_currency, flight_type, layover_count, carbon_emissions_flight,
                 carbon_emissions_typical, carbon_emissions_difference_percent,
                 departure_token, booking_token, airline_logo_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, flight_result_data)
            
            flight_result_id = cursor.lastrowid
            
            # Store flight segments
            if 'flights' in flight_data:
                for order, segment in enumerate(flight_data['flights'], 1):
                    self._store_flight_segment(cursor, flight_result_id, segment, order)
            
            # Store layovers
            if 'layovers' in flight_data:
                for order, layover in enumerate(flight_data['layovers'], 1):
                    self._store_layover(cursor, flight_result_id, layover, order)
            
            conn.commit()
            
        finally:
            conn.close()
    
    def _store_flight_segment(self, cursor, flight_result_id: int, 
                            segment: Dict[str, Any], order: int):
        """Store individual flight segment"""
        
        departure_airport = segment.get('departure_airport', {})
        arrival_airport = segment.get('arrival_airport', {})
        
        segment_data = (
            flight_result_id,
            order,
            departure_airport.get('id'),
            departure_airport.get('name'),
            departure_airport.get('time'),
            arrival_airport.get('id'),
            arrival_airport.get('name'),
            arrival_airport.get('time'),
            segment.get('duration'),
            segment.get('airplane'),
            segment.get('airline_code'),
            segment.get('airline'),
            segment.get('airline_logo'),
            segment.get('flight_number'),
            segment.get('travel_class'),
            segment.get('legroom'),
            segment.get('overnight', False),
            segment.get('often_delayed_by_over_30_min', False),
            json.dumps(segment.get('ticket_also_sold_by', [])),
            json.dumps(segment.get('extensions', [])),
            segment.get('plane_and_crew_by')
        )
        
        cursor.execute("""
            INSERT INTO flight_segments 
            (flight_result_id, segment_order, departure_airport_id, departure_airport_name,
             departure_time, arrival_airport_id, arrival_airport_name, arrival_time,
             duration_minutes, airplane_model, airline_code, airline_name, airline_logo_url,
             flight_number, travel_class, legroom, is_overnight, often_delayed,
             ticket_also_sold_by, extensions, plane_and_crew_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, segment_data)
    
    def _store_layover(self, cursor, flight_result_id: int, 
                      layover: Dict[str, Any], order: int):
        """Store layover information"""
        
        layover_data = (
            flight_result_id,
            order,
            layover.get('id'),
            layover.get('name'),
            layover.get('duration'),
            layover.get('overnight', False)
        )
        
        cursor.execute("""
            INSERT INTO layovers 
            (flight_result_id, layover_order, airport_id, airport_name, 
             duration_minutes, is_overnight)
            VALUES (?, ?, ?, ?, ?, ?)
        """, layover_data)
    
    def _extract_airlines(self, response: Dict[str, Any]) -> int:
        """Extract and store airline information"""
        
        airlines_stored = 0
        airlines_seen = set()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Extract from flight segments
            for flight_group in ['best_flights', 'other_flights']:
                if flight_group in response:
                    for flight in response[flight_group]:
                        if 'flights' in flight:
                            for segment in flight['flights']:
                                airline_code = segment.get('airline_code')
                                airline_name = segment.get('airline')
                                airline_logo = segment.get('airline_logo')
                                
                                if airline_code and airline_code not in airlines_seen:
                                    self._store_airline(cursor, airline_code, airline_name, airline_logo)
                                    airlines_seen.add(airline_code)
                                    airlines_stored += 1
            
            conn.commit()
            
        finally:
            conn.close()
        
        return airlines_stored
    
    def _store_airline(self, cursor, code: str, name: str, logo_url: str):
        """Store individual airline information"""
        
        airline_data = (
            code,
            name,
            logo_url,
            datetime.now().isoformat()
        )
        
        cursor.execute("""
            INSERT OR REPLACE INTO airlines 
            (airline_code, airline_name, logo_url, last_seen)
            VALUES (?, ?, ?, ?)
        """, airline_data)
    
    def _store_price_insights(self, search_id: str, response: Dict[str, Any]):
        """Store price insights data"""
        
        if 'price_insights' not in response:
            return
        
        price_insights = response['price_insights']
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            typical_range = price_insights.get('typical_price_range', [])
            
            insights_data = (
                search_id,
                price_insights.get('lowest_price'),
                price_insights.get('price_level'),
                typical_range[0] if len(typical_range) > 0 else None,
                typical_range[1] if len(typical_range) > 1 else None,
                json.dumps(price_insights.get('price_history', []))
            )
            
            cursor.execute("""
                INSERT INTO price_insights 
                (search_id, lowest_price, price_level, typical_price_low, 
                 typical_price_high, price_history)
                VALUES (?, ?, ?, ?, ?, ?)
            """, insights_data)
            
            conn.commit()
            
        finally:
            conn.close()
    
    def _update_route_analytics(self, params: Dict[str, Any], response: Dict[str, Any]):
        """Update route analytics data"""
        
        departure_id = params.get('departure_id')
        arrival_id = params.get('arrival_id')
        
        if not departure_id or not arrival_id:
            return
        
        route_key = f"{departure_id}-{arrival_id}"
        
        # Calculate average price from results
        prices = []
        for flight_group in ['best_flights', 'other_flights']:
            if flight_group in response:
                for flight in response[flight_group]:
                    if 'price' in flight:
                        prices.append(flight['price'])
        
        if not prices:
            return
        
        avg_price = sum(prices) // len(prices)
        min_price = min(prices)
        max_price = max(prices)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Update or insert route analytics
            cursor.execute("""
                INSERT OR REPLACE INTO route_analytics 
                (route_key, departure_airport, arrival_airport, total_searches, 
                 avg_price, min_price, max_price, last_search_date, updated_at)
                VALUES (?, ?, ?, 
                        COALESCE((SELECT total_searches FROM route_analytics WHERE route_key = ?) + 1, 1),
                        ?, ?, ?, ?, ?)
            """, (route_key, departure_id, arrival_id, route_key, 
                  avg_price, min_price, max_price, 
                  params.get('outbound_date'), datetime.now().isoformat()))
            
            conn.commit()
            
        finally:
            conn.close()

def test_processor():
    """Test the flight data processor"""
    print("🧪 Testing Flight Data Processor...")
    
    try:
        processor = FlightDataProcessor()
        print("✅ Processor initialized successfully")
        
        # Create mock search result
        mock_result = {
            'search_id': 'test_search_123',
            'search_timestamp': datetime.now().isoformat(),
            'search_parameters': {
                'departure_id': 'LAX',
                'arrival_id': 'JFK',
                'outbound_date': '2025-09-15',
                'return_date': '2025-09-22',
                'adults': 2,
                'currency': 'USD'
            },
            'raw_response': {
                'search_metadata': {'status': 'Success'},
                'best_flights': [
                    {
                        'price': 599,
                        'total_duration': 360,
                        'type': 'Round trip',
                        'flights': [
                            {
                                'departure_airport': {'id': 'LAX', 'name': 'Los Angeles International'},
                                'arrival_airport': {'id': 'JFK', 'name': 'John F. Kennedy International'},
                                'airline': 'American Airlines',
                                'airline_code': 'AA',
                                'flight_number': 'AA 123'
                            }
                        ],
                        'layovers': []
                    }
                ],
                'airports': [
                    {
                        'departure': [
                            {
                                'airport': {'id': 'LAX', 'name': 'Los Angeles International'},
                                'city': 'Los Angeles',
                                'country': 'United States'
                            }
                        ]
                    }
                ]
            },
            'status': 'success'
        }
        
        # Process mock data
        stats = processor.process_search_response(mock_result)
        print(f"✅ Processing completed: {stats}")
        
        print("🎉 Processor test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Processor test failed: {e}")
        return False

if __name__ == "__main__":
    test_processor()
