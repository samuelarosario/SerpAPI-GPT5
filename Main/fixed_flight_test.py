"""
Fixed Flight Test - Shows actual API errors properly
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_flight_search import EnhancedFlightSearchClient

def test_with_error_display():
    """Test flight search with proper error display"""
    print("🧪 Testing Flight Search with Error Display...")
    
    try:
        client = EnhancedFlightSearchClient()
        print("✅ Client initialized successfully")
        
        # Test POM to MNL
        print("\n🔍 Testing POM to MNL flight search...")
        result = client.search_flights(
            departure_id='POM',
            arrival_id='MNL',
            outbound_date='2025-09-26'
        )
        
        print(f"📊 Result Keys: {list(result.keys())}")
        print(f"📊 Success: {result.get('success', 'Unknown')}")
        print(f"📊 Source: {result.get('source', 'Unknown')}")
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
            
        if 'data' in result and result['data']:
            print(f"✅ Data found: {len(result['data'])} items")
        else:
            print("❓ No data in result")
            
        # Display full result for debugging
        print(f"\n📋 Full Result: {result}")
        
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_with_error_display()
