"""
SerpAPI Flight Data System - Complete Demonstration
Shows integration of all components: Client, Processor, and Analyzer
"""

import json
import time
from datetime import datetime, timedelta

from serpapi_client import SerpAPIFlightClient, FlightSearchValidator
from flight_processor import FlightDataProcessor
from flight_analyzer import FlightAnalyzer
from config import validate_config

class FlightDataSystem:
    """Complete flight data collection and analysis system"""
    
    def __init__(self):
        """Initialize the complete system"""
        self.client = None
        self.processor = FlightDataProcessor()
        self.analyzer = FlightAnalyzer()
        
        # Validate configuration
        config_status = validate_config()
        if not config_status['valid']:
            print("⚠️ Configuration issues detected:")
            for issue in config_status['issues']:
                print(f"   - {issue}")
        
        # Initialize client if API key is available
        if config_status['api_key_available']:
            try:
                self.client = SerpAPIFlightClient()
                print("✅ SerpAPI client initialized")
            except Exception as e:
                print(f"⚠️ Could not initialize SerpAPI client: {e}")
                self.client = None
        else:
            print("⚠️ SerpAPI client not available (no API key)")
    
    def search_and_store_flights(self, departure_id: str, arrival_id: str, 
                               outbound_date: str, return_date: str = None, **kwargs) -> dict:
        """
        Complete workflow: search flights, store data, return analysis
        """
        
        if not self.client:
            return self._simulate_search_and_store(departure_id, arrival_id, outbound_date, return_date, **kwargs)
        
        try:
            print(f"🔍 Searching flights: {departure_id} → {arrival_id}")
            print(f"📅 Departure: {outbound_date}" + (f", Return: {return_date}" if return_date else ""))
            
            # Search flights
            if return_date:
                search_result = self.client.search_round_trip(
                    departure_id, arrival_id, outbound_date, return_date, **kwargs
                )
            else:
                search_result = self.client.search_one_way(
                    departure_id, arrival_id, outbound_date, **kwargs
                )
            
            print(f"✅ Search completed: {search_result['search_id']}")
            
            # Process and store data
            print("💾 Processing and storing flight data...")
            processing_stats = self.processor.process_search_response(search_result)
            
            print(f"✅ Data processing completed:")
            print(f"   - Flights processed: {processing_stats['flights_processed']}")
            print(f"   - Airlines extracted: {processing_stats['airlines_extracted']}")
            print(f"   ℹ️ Airports updated via centralized method in enhanced_flight_search")
            
            if processing_stats['errors']:
                print(f"⚠️ Processing errors: {len(processing_stats['errors'])}")
                for error in processing_stats['errors']:
                    print(f"   - {error}")
            
            return {
                'success': True,
                'search_id': search_result['search_id'],
                'processing_stats': processing_stats,
                'search_result': search_result
            }
            
        except Exception as e:
            print(f"❌ Search and store failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _simulate_search_and_store(self, departure_id: str, arrival_id: str, 
                                 outbound_date: str, return_date: str = None, **kwargs) -> dict:
        """Simulate search and store with mock data (when no API key available)"""
        
        print(f"🧪 SIMULATION MODE: {departure_id} → {arrival_id}")
        print("(No API key available - using mock data)")
        
        # Create mock search result
        search_id = f"sim_{departure_id}_{arrival_id}_{int(time.time())}"
        
        mock_result = {
            'search_id': search_id,
            'search_timestamp': datetime.now().isoformat(),
            'search_parameters': {
                'departure_id': departure_id,
                'arrival_id': arrival_id,
                'outbound_date': outbound_date,
                'return_date': return_date,
                'adults': kwargs.get('adults', 1),
                'currency': kwargs.get('currency', 'USD'),
                'type': 1 if return_date else 2
            },
            'raw_response': {
                'search_metadata': {'status': 'Success'},
                'best_flights': [
                    {
                        'price': 599,
                        'total_duration': 360,
                        'type': 'Round trip' if return_date else 'One way',
                        'flights': [
                            {
                                'departure_airport': {
                                    'id': departure_id, 
                                    'name': f'{departure_id} Airport',
                                    'time': f'{outbound_date} 08:00'
                                },
                                'arrival_airport': {
                                    'id': arrival_id, 
                                    'name': f'{arrival_id} Airport',
                                    'time': f'{outbound_date} 14:00'
                                },
                                'airline': 'Mock Airlines',
                                'airline_code': 'MK',
                                'flight_number': 'MK 123',
                                'duration': 360
                            }
                        ],
                        'layovers': []
                    }
                ],
                'airports': [
                    {
                        'departure': [
                            {
                                'airport': {'id': departure_id, 'name': f'{departure_id} Airport'},
                                'city': 'Mock City',
                                'country': 'Mock Country'
                            }
                        ],
                        'arrival': [
                            {
                                'airport': {'id': arrival_id, 'name': f'{arrival_id} Airport'},
                                'city': 'Mock City',
                                'country': 'Mock Country'
                            }
                        ]
                    }
                ]
            },
            'status': 'success'
        }
        
        # Process mock data
        processing_stats = self.processor.process_search_response(mock_result)
        
        print(f"✅ Mock data processed: {search_id}")
        
        return {
            'success': True,
            'search_id': search_id,
            'processing_stats': processing_stats,
            'simulation': True
        }
    
    def analyze_route(self, departure_id: str, arrival_id: str) -> dict:
        """Analyze data for a specific route"""
        
        route_key = f"{departure_id}-{arrival_id}"
        print(f"📊 Analyzing route: {route_key}")
        
        try:
            # Get route insights
            route_insights = self.analyzer.get_route_insights(route_key)
            
            # Get price analysis for this route
            price_analysis = self.analyzer.get_price_analysis(departure_id, arrival_id)
            
            # Get duration analysis
            duration_analysis = self.analyzer.get_duration_analysis(departure_id, arrival_id)
            
            return {
                'route_insights': route_insights,
                'price_analysis': price_analysis,
                'duration_analysis': duration_analysis
            }
            
        except Exception as e:
            print(f"❌ Route analysis failed: {e}")
            return {'error': str(e)}
    
    def generate_system_report(self) -> str:
        """Generate comprehensive system report"""
        
        print("📋 Generating system report...")
        
        try:
            # Get overall analysis
            report = self.analyzer.generate_report()
            
            # Add system statistics
            search_summary = self.analyzer.get_search_summary(30)
            airline_analysis = self.analyzer.get_airline_analysis()
            
            additional_info = [
                "",
                "🔧 SYSTEM STATISTICS",
                "-" * 40,
                f"Database Path: {self.processor.db_path}",
                f"API Client Available: {'Yes' if self.client else 'No'}",
                f"Total Routes Analyzed: {len(self.analyzer.get_route_insights().get('top_routes', []))}",
                f"Total Airlines in Database: {len(airline_analysis.get('most_frequent_airlines', []))}",
                ""
            ]
            
            return report + "\n".join(additional_info)
            
        except Exception as e:
            return f"Error generating report: {e}"

def demo_flight_search_system():
    """Demonstrate the complete flight search system"""
    
    print("🚀 SerpAPI Flight Data System Demonstration")
    print("=" * 60)
    
    # Initialize system
    system = FlightDataSystem()
    print("")
    
    # Demo search parameters
    demo_searches = [
        {
            'departure_id': 'LAX',
            'arrival_id': 'JFK',
            'outbound_date': '2025-09-15',
            'return_date': '2025-09-22',
            'adults': 2
        },
        {
            'departure_id': 'SFO',
            'arrival_id': 'ORD',
            'outbound_date': '2025-09-20',
            'return_date': '2025-09-27',
            'adults': 1
        },
        {
            'departure_id': 'MIA',
            'arrival_id': 'LAX',
            'outbound_date': '2025-09-25',
            # One way flight
            'adults': 1
        }
    ]
    
    # Perform searches
    search_results = []
    for i, search_params in enumerate(demo_searches, 1):
        print(f"\n🔍 Demo Search {i}/{len(demo_searches)}")
        print("-" * 30)
        
        result = system.search_and_store_flights(**search_params)
        search_results.append(result)
        
        if result['success']:
            print(f"✅ Search {i} completed successfully")
        else:
            print(f"❌ Search {i} failed: {result['error']}")
        
        # Small delay between searches
        time.sleep(1)
    
    # Analyze routes
    print(f"\n📊 Route Analysis")
    print("-" * 30)
    
    for search_params in demo_searches:
        departure_id = search_params['departure_id']
        arrival_id = search_params['arrival_id']
        
        analysis = system.analyze_route(departure_id, arrival_id)
        
        if 'error' not in analysis:
            route_key = f"{departure_id}-{arrival_id}"
            print(f"✅ Route {route_key} analyzed")
            
            # Show key insights
            if 'route_insights' in analysis and 'error' not in analysis['route_insights']:
                insights = analysis['route_insights']
                print(f"   Searches: {insights.get('total_searches', 'N/A')}")
                print(f"   Avg Price: ${insights.get('avg_price', 'N/A')}")
        else:
            print(f"⚠️ Analysis failed for {departure_id}-{arrival_id}")
    
    # Generate comprehensive report
    print(f"\n📋 System Report")
    print("-" * 30)
    
    report = system.generate_system_report()
    
    # Save report to file
    report_filename = f"../Temp/flight_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    try:
        with open(report_filename, 'w') as f:
            f.write(report)
        print(f"✅ Report saved to: {report_filename}")
    except Exception as e:
        print(f"⚠️ Could not save report: {e}")
    
    # Show summary
    successful_searches = sum(1 for result in search_results if result['success'])
    
    print(f"\n🎯 Demo Summary")
    print("-" * 30)
    print(f"Total Searches: {len(demo_searches)}")
    print(f"Successful: {successful_searches}")
    print(f"Failed: {len(demo_searches) - successful_searches}")
    print(f"System Status: {'Operational' if successful_searches > 0 else 'Issues Detected'}")
    
    print("\n" + "=" * 60)
    print("✅ Demonstration completed!")
    
    return system

if __name__ == "__main__":
    demo_flight_search_system()
