"""
Simple API Approval Test
========================

This script demonstrates the streamlined API approval system that shows
immediate prompts for each API call without complex pending request management.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_flight_search import EnhancedFlightSearchClient

def test_simple_approval():
    """Test the simple approval system"""
    
    print("🔍 TESTING: Simple API Approval System")
    print("=" * 55)
    print("This system will prompt you for approval before each API call.")
    print("You can simply type 'y' to approve or 'n' to decline.")
    print()
    
    # Initialize client
    client = EnhancedFlightSearchClient()
    
    print("📋 Test Scenario 1: POM to MNL Flight Search")
    print("-" * 45)
    print("This search will check cache first, then prompt for API approval if needed.")
    print()
    
    # Test search - this will trigger approval prompt if cache miss
    result1 = client.search_flights(
        departure_id='POM',
        arrival_id='MNL',
        outbound_date='2025-09-26',
        force_api=False  # Check cache first
    )
    
    print(f"\n📊 Result 1:")
    print(f"   Success: {result1.get('success')}")
    print(f"   Source: {result1.get('source')}")
    
    if result1.get('success'):
        data = result1.get('data', {})
        if 'best_flights' in data:
            flights = data['best_flights']
            print(f"   Found: {len(flights)} flight options")
            if flights:
                cheapest = min(flights, key=lambda x: x.get('price', float('inf')))
                print(f"   Cheapest: ${cheapest.get('price', 'N/A')}")
    else:
        print(f"   Error: {result1.get('error', 'Unknown error')}")
    
    print("\n" + "="*55)
    print("📋 Test Scenario 2: Different Route Search")
    print("-" * 45)
    print("Testing with a different route (likely to need API call).")
    print()
    
    # Test different route
    result2 = client.search_flights(
        departure_id='SYD',  # Sydney
        arrival_id='TOK',    # Tokyo
        outbound_date='2025-11-01',
        return_date='2025-11-08',
        force_api=False
    )
    
    print(f"\n📊 Result 2:")
    print(f"   Success: {result2.get('success')}")
    print(f"   Source: {result2.get('source')}")
    
    if result2.get('success'):
        data = result2.get('data', {})
        if 'best_flights' in data:
            flights = data['best_flights']
            print(f"   Found: {len(flights)} flight options")
    else:
        print(f"   Error: {result2.get('error', 'Unknown error')}")
    
    print("\n" + "="*55)
    print("✅ Test Complete!")
    print("="*55)
    
    # Show final usage
    from simple_api_approval import api_approval
    stats = api_approval._get_usage_stats()
    print(f"\n📊 Today's API Usage:")
    print(f"   Total Calls: {stats['total_calls']}")
    print(f"   Total Cost: ${stats['total_cost_usd']:.4f} USD")

if __name__ == "__main__":
    test_simple_approval()
