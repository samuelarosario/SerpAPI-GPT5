"""
Direct SerpAPI Client Test - Bypass enhanced client
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from serpapi_client import SerpAPIFlightClient

def test_direct_client():
    """Test SerpAPI client directly"""
    print("🧪 Testing SerpAPI Client Directly...")
    
    try:
        client = SerpAPIFlightClient()
        print("✅ Client initialized successfully")
        print(f"🔑 API Key: {client.api_key[:10]}...")
        
        # Test a simple search
        print("\n🔍 Testing direct search...")
        result = client.search_one_way(
            departure_id='POM',
            arrival_id='MNL',
            outbound_date='2025-09-26'
        )
        
        print(f"📊 Result Keys: {list(result.keys())}")
        print(f"📊 Success: {result.get('success', 'Unknown')}")
        print(f"📊 Status: {result.get('status', 'Unknown')}")
        print(f"📊 Error: {result.get('error', 'None')}")
        
        # Display full result for debugging  
        print(f"\n📋 Full Result: {result}")
        
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_client()
