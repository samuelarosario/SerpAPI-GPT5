"""
Debug API Test - Detailed investigation of API response
"""
import os
import requests
from urllib.parse import urlencode
import json

def test_direct_api_call():
    """Test direct API call to understand response format"""
    print("🔍 Testing Direct API Call...")
    
    # Get API key
    api_key = os.getenv('SERPAPI_API_KEY')
    if not api_key:
        print("❌ No API key found in environment variables")
        return
        
    print(f"✅ API Key found: {api_key[:10]}...")
    
    # Set up parameters
    params = {
        'engine': 'google_flights',
        'departure_id': 'POM',
        'arrival_id': 'MNL', 
        'outbound_date': '2025-09-26',
        'currency': 'USD',
        'hl': 'en',
        'api_key': api_key
    }
    
    # Build URL
    base_url = "https://serpapi.com/search"
    url = f"{base_url}?{urlencode(params)}"
    
    print(f"🌐 URL: {url[:100]}...")
    
    try:
        # Make request
        print("📡 Making request...")
        response = requests.get(url, timeout=30)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📊 Headers: {dict(response.headers)}")
        
        # Try to get JSON
        try:
            data = response.json()
            print(f"📊 Response Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            # Print first 500 chars of response
            print(f"📊 Response Preview: {json.dumps(data, indent=2)[:500]}...")
            
            # Check for specific fields
            if 'error' in data:
                print(f"❌ API Error: {data['error']}")
            
            if 'search_metadata' in data:
                print(f"✅ Search metadata found: {data['search_metadata']}")
                
            if 'best_flights' in data:
                print(f"✅ Best flights found: {len(data['best_flights'])} flights")
            elif 'other_flights' in data:
                print(f"✅ Other flights found: {len(data['other_flights'])} flights")
            elif 'flights' in data:
                print(f"✅ Flights found: {len(data['flights'])} flights")
            else:
                print("❓ No flight data found in response")
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            print(f"📊 Raw response: {response.text[:500]}...")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_direct_api_call()
