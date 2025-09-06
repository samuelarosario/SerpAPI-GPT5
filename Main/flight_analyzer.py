"""
Flight Data Analyzer
Provides analysis and reporting capabilities for flight data
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import statistics

class FlightAnalyzer:
    """Analyzes flight data and provides insights"""
    
    def __init__(self, db_path: str = "../DB/Main_DB.db"):
        """Initialize the analyzer"""
        self.db_path = db_path
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def get_search_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get summary of searches in the last N days"""
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Total searches
            cursor.execute("""
                SELECT COUNT(*) FROM flight_searches 
                WHERE search_timestamp > ?
            """, (cutoff_date,))
            total_searches = cursor.fetchone()[0]
            
            # Popular routes
            cursor.execute("""
                SELECT departure_id, arrival_id, COUNT(*) as search_count
                FROM flight_searches 
                WHERE search_timestamp > ?
                GROUP BY departure_id, arrival_id
                ORDER BY search_count DESC
                LIMIT 10
            """, (cutoff_date,))
            popular_routes = cursor.fetchall()
            
            # Search by flight type
            cursor.execute("""
                SELECT flight_type, COUNT(*) as count
                FROM flight_searches 
                WHERE search_timestamp > ?
                GROUP BY flight_type
            """, (cutoff_date,))
            flight_types = cursor.fetchall()
            
            # Search by travel class
            cursor.execute("""
                SELECT travel_class, COUNT(*) as count
                FROM flight_searches 
                WHERE search_timestamp > ?
                GROUP BY travel_class
            """, (cutoff_date,))
            travel_classes = cursor.fetchall()
            
            return {
                'period_days': days,
                'total_searches': total_searches,
                'popular_routes': [
                    {'route': f"{route[0]}-{route[1]}", 'searches': route[2]}
                    for route in popular_routes
                ],
                'flight_types': [
                    {'type': self._get_flight_type_name(ft[0]), 'count': ft[1]}
                    for ft in flight_types
                ],
                'travel_classes': [
                    {'class': self._get_travel_class_name(tc[0]), 'count': tc[1]}
                    for tc in travel_classes
                ]
            }
            
        finally:
            conn.close()
    
    def get_price_analysis(self, departure_id: str = None, arrival_id: str = None) -> Dict[str, Any]:
        """Analyze flight prices for specific route or overall"""
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Build query based on parameters
            where_clause = "1=1"
            params = []
            
            if departure_id:
                where_clause += " AND fs.departure_id = ?"
                params.append(departure_id)
            
            if arrival_id:
                where_clause += " AND fs.arrival_id = ?"
                params.append(arrival_id)
            
            # Get price statistics
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as flight_count,
                    AVG(fr.total_price) as avg_price,
                    MIN(fr.total_price) as min_price,
                    MAX(fr.total_price) as max_price,
                    fr.price_currency
                FROM flight_results fr
                JOIN flight_searches fs ON fr.search_id = fs.search_id
                WHERE {where_clause} AND fr.total_price IS NOT NULL
                GROUP BY fr.price_currency
            """, params)
            
            price_stats = cursor.fetchall()
            
            # Get price distribution
            cursor.execute(f"""
                SELECT fr.total_price
                FROM flight_results fr
                JOIN flight_searches fs ON fr.search_id = fs.search_id
                WHERE {where_clause} AND fr.total_price IS NOT NULL
                ORDER BY fr.total_price
            """, params)
            
            prices = [row[0] for row in cursor.fetchall()]
            
            analysis = {
                'route': f"{departure_id or 'ANY'}-{arrival_id or 'ANY'}",
                'statistics': [],
                'distribution': self._calculate_price_distribution(prices) if prices else {}
            }
            
            for stats in price_stats:
                analysis['statistics'].append({
                    'currency': stats[4],
                    'flight_count': stats[0],
                    'average_price': round(stats[1], 2) if stats[1] else 0,
                    'min_price': stats[2],
                    'max_price': stats[3],
                    'median_price': statistics.median(prices) if prices else 0
                })
            
            return analysis
            
        finally:
            conn.close()
    
    def get_airline_analysis(self) -> Dict[str, Any]:
        """Analyze airline performance and popularity"""
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Airline frequency
            cursor.execute("""
                SELECT a.airline_name, a.airline_code, COUNT(*) as flight_count
                FROM flight_segments fs
                JOIN airlines a ON fs.airline_code = a.airline_code
                GROUP BY a.airline_code, a.airline_name
                ORDER BY flight_count DESC
            """)
            airline_frequency = cursor.fetchall()
            
            # Average prices by airline
            cursor.execute("""
                SELECT a.airline_name, AVG(fr.total_price) as avg_price, COUNT(*) as flights
                FROM flight_segments fs
                JOIN airlines a ON fs.airline_code = a.airline_code
                JOIN flight_results fr ON fs.flight_result_id = fr.id
                WHERE fr.total_price IS NOT NULL
                GROUP BY a.airline_code, a.airline_name
                HAVING COUNT(*) >= 3
                ORDER BY avg_price ASC
            """)
            airline_prices = cursor.fetchall()
            
            # On-time performance (based on delay flags)
            cursor.execute("""
                SELECT a.airline_name, 
                       SUM(CASE WHEN fs.often_delayed = 1 THEN 1 ELSE 0 END) as delayed_flights,
                       COUNT(*) as total_flights
                FROM flight_segments fs
                JOIN airlines a ON fs.airline_code = a.airline_code
                GROUP BY a.airline_code, a.airline_name
                HAVING COUNT(*) >= 5
            """)
            airline_delays = cursor.fetchall()
            
            return {
                'most_frequent_airlines': [
                    {'name': row[0], 'code': row[1], 'flights': row[2]}
                    for row in airline_frequency[:10]
                ],
                'most_affordable_airlines': [
                    {'name': row[0], 'avg_price': round(row[1], 2), 'flights': row[2]}
                    for row in airline_prices[:10]
                ],
                'airline_reliability': [
                    {
                        'name': row[0],
                        'delay_rate': round((row[1] / row[2]) * 100, 1) if row[2] > 0 else 0,
                        'total_flights': row[2]
                    }
                    for row in airline_delays
                ]
            }
            
        finally:
            conn.close()
    
    def get_route_insights(self, route_key: str = None) -> Dict[str, Any]:
        """Get insights for specific route or top routes"""
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if route_key:
                # Specific route analysis
                cursor.execute("""
                    SELECT * FROM route_analytics WHERE route_key = ?
                """, (route_key,))
                route_data = cursor.fetchone()
                
                if not route_data:
                    return {'error': f'No data found for route {route_key}'}
                
                # Get recent searches for this route
                departure_id, arrival_id = route_key.split('-')
                cursor.execute("""
                    SELECT search_timestamp, total_results
                    FROM flight_searches 
                    WHERE departure_id = ? AND arrival_id = ?
                    ORDER BY search_timestamp DESC
                    LIMIT 10
                """, (departure_id, arrival_id))
                recent_searches = cursor.fetchall()
                
                return {
                    'route': route_key,
                    'departure_airport': route_data[2],
                    'arrival_airport': route_data[3],
                    'total_searches': route_data[4],
                    'avg_price': route_data[5],
                    'min_price': route_data[6],
                    'max_price': route_data[7],
                    'last_search_date': route_data[8],
                    'price_trend': route_data[9],
                    'recent_searches': len(recent_searches)
                }
            
            else:
                # Top routes analysis
                cursor.execute("""
                    SELECT route_key, departure_airport, arrival_airport, 
                           total_searches, avg_price, price_trend
                    FROM route_analytics
                    ORDER BY total_searches DESC
                    LIMIT 20
                """)
                top_routes = cursor.fetchall()
                
                return {
                    'top_routes': [
                        {
                            'route': row[0],
                            'departure': row[1],
                            'arrival': row[2],
                            'searches': row[3],
                            'avg_price': row[4],
                            'trend': row[5]
                        }
                        for row in top_routes
                    ]
                }
                
        finally:
            conn.close()
    
    def get_duration_analysis(self, departure_id: str = None, arrival_id: str = None) -> Dict[str, Any]:
        """Analyze flight durations"""
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            where_clause = "1=1"
            params = []
            
            if departure_id:
                where_clause += " AND fs.departure_id = ?"
                params.append(departure_id)
            
            if arrival_id:
                where_clause += " AND fs.arrival_id = ?"
                params.append(arrival_id)
            
            # Duration statistics
            cursor.execute(f"""
                SELECT 
                    AVG(fr.total_duration) as avg_duration,
                    MIN(fr.total_duration) as min_duration,
                    MAX(fr.total_duration) as max_duration,
                    COUNT(*) as flight_count
                FROM flight_results fr
                JOIN flight_searches fs ON fr.search_id = fs.search_id
                WHERE {where_clause} AND fr.total_duration IS NOT NULL
            """, params)
            
            duration_stats = cursor.fetchone()
            
            # Duration by layover count
            cursor.execute(f"""
                SELECT 
                    fr.layover_count,
                    AVG(fr.total_duration) as avg_duration,
                    COUNT(*) as flight_count
                FROM flight_results fr
                JOIN flight_searches fs ON fr.search_id = fs.search_id
                WHERE {where_clause} AND fr.total_duration IS NOT NULL
                GROUP BY fr.layover_count
                ORDER BY fr.layover_count
            """, params)
            
            duration_by_stops = cursor.fetchall()
            
            return {
                'route': f"{departure_id or 'ANY'}-{arrival_id or 'ANY'}",
                'overall_stats': {
                    'avg_duration_hours': round(duration_stats[0] / 60, 1) if duration_stats[0] else 0,
                    'min_duration_hours': round(duration_stats[1] / 60, 1) if duration_stats[1] else 0,
                    'max_duration_hours': round(duration_stats[2] / 60, 1) if duration_stats[2] else 0,
                    'total_flights': duration_stats[3]
                },
                'duration_by_stops': [
                    {
                        'stops': row[0],
                        'avg_duration_hours': round(row[1] / 60, 1),
                        'flight_count': row[2]
                    }
                    for row in duration_by_stops
                ]
            }
            
        finally:
            conn.close()
    
    def _calculate_price_distribution(self, prices: List[int]) -> Dict[str, Any]:
        """Calculate price distribution statistics"""
        
        if not prices:
            return {}
        
        sorted_prices = sorted(prices)
        count = len(sorted_prices)
        
        return {
            'count': count,
            'quartiles': {
                'q1': sorted_prices[count // 4],
                'q2': sorted_prices[count // 2],  # median
                'q3': sorted_prices[3 * count // 4]
            },
            'percentiles': {
                'p10': sorted_prices[count // 10],
                'p90': sorted_prices[9 * count // 10]
            },
            'standard_deviation': round(statistics.stdev(prices), 2) if count > 1 else 0
        }
    
    def _get_flight_type_name(self, type_code: int) -> str:
        """Convert flight type code to name"""
        types = {1: 'Round Trip', 2: 'One Way', 3: 'Multi-City'}
        return types.get(type_code, f'Unknown ({type_code})')
    
    def _get_travel_class_name(self, class_code: int) -> str:
        """Convert travel class code to name"""
        classes = {1: 'Economy', 2: 'Premium Economy', 3: 'Business', 4: 'First'}
        return classes.get(class_code, f'Unknown ({class_code})')
    
    def generate_report(self, route: str = None) -> str:
        """Generate a comprehensive analysis report"""
        
        report = []
        report.append("=" * 60)
        report.append("FLIGHT DATA ANALYSIS REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Search Summary
        summary = self.get_search_summary()
        report.append("📊 SEARCH SUMMARY (Last 30 Days)")
        report.append("-" * 40)
        report.append(f"Total Searches: {summary['total_searches']}")
        report.append("")
        
        if summary['popular_routes']:
            report.append("🛫 Top Routes:")
            for route_info in summary['popular_routes'][:5]:
                report.append(f"  {route_info['route']}: {route_info['searches']} searches")
        
        report.append("")
        
        # Price Analysis
        price_analysis = self.get_price_analysis()
        if price_analysis['statistics']:
            report.append("💰 PRICE ANALYSIS")
            report.append("-" * 40)
            for stat in price_analysis['statistics']:
                report.append(f"Currency: {stat['currency']}")
                report.append(f"  Flights Analyzed: {stat['flight_count']}")
                report.append(f"  Average Price: ${stat['average_price']}")
                report.append(f"  Price Range: ${stat['min_price']} - ${stat['max_price']}")
                report.append(f"  Median Price: ${stat['median_price']}")
        
        report.append("")
        
        # Airline Analysis
        airline_analysis = self.get_airline_analysis()
        if airline_analysis['most_frequent_airlines']:
            report.append("✈️ AIRLINE ANALYSIS")
            report.append("-" * 40)
            report.append("Most Frequent Airlines:")
            for airline in airline_analysis['most_frequent_airlines'][:5]:
                report.append(f"  {airline['name']} ({airline['code']}): {airline['flights']} flights")
        
        report.append("")
        
        # Route Insights
        if route:
            route_insights = self.get_route_insights(route)
            if 'error' not in route_insights:
                report.append(f"🗺️ ROUTE ANALYSIS: {route}")
                report.append("-" * 40)
                report.append(f"Total Searches: {route_insights['total_searches']}")
                report.append(f"Average Price: ${route_insights['avg_price']}")
                report.append(f"Price Range: ${route_insights['min_price']} - ${route_insights['max_price']}")
                report.append(f"Price Trend: {route_insights['price_trend']}")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)

def test_analyzer():
    """Test the flight analyzer"""
    print("🧪 Testing Flight Analyzer...")
    
    try:
        analyzer = FlightAnalyzer()
        print("✅ Analyzer initialized successfully")
        
        # Test search summary
        summary = analyzer.get_search_summary(7)
        print(f"✅ Search summary: {summary['total_searches']} searches found")
        
        # Test price analysis
        price_analysis = analyzer.get_price_analysis()
        print(f"✅ Price analysis completed")
        
        # Test airline analysis
        airline_analysis = analyzer.get_airline_analysis()
        print(f"✅ Airline analysis completed")
        
        # Generate sample report
        report = analyzer.generate_report()
        print("✅ Report generated successfully")
        
        print("🎉 Analyzer test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Analyzer test failed: {e}")
        return False

if __name__ == "__main__":
    test_analyzer()
