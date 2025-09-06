"""
Direct SerpAPI Test
Tests the original SerpAPI client directly
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Main'))

from serpapi_client import SerpAPIFlightClient

def direct_api_test():
    """Test direct API call"""
    
    print("🔧 DIRECT SERPAPI CLIENT TEST")
    print("=" * 40)
    
    try:
        # Test environment variable first
        api_key = os.environ.get('SERPAPI_KEY')
        print(f"🔑 API Key: {api_key[:16]}...{api_key[-4:] if api_key else 'Not found'}")
        
        if not api_key:
            print("❌ No API key found in environment")
            return False
            
        # Initialize direct client
        client = SerpAPIFlightClient(api_key)
        print("✅ Direct SerpAPI client initialized")
        
        # Test simple search
        print(f"\n🧪 Testing direct API call...")
        
        try:
            result = client.search_one_way(
                departure_id='LAX',
                arrival_id='JFK',
                outbound_date='2025-09-26',
                adults=1
            )
            
            print(f"Direct API Result:")
            print(f"   Success: {result.get('success', False)}")
            if result.get('success'):
                print(f"   Search ID: {result.get('data', {}).get('search_id', 'N/A')}")
            else:
                print(f"   Error: {result.get('error', 'No error message')}")
                
            return result.get('success', False)
            
        except Exception as e:
            print(f"❌ Direct API call failed: {e}")
            return False
        
    except Exception as e:
        print(f"❌ Client initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = direct_api_test()
    if success:
        print("\n✅ Direct API test successful!")
    else:
        print("\n❌ Direct API test failed!")
