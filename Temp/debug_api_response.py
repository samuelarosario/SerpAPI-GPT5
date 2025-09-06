#!/usr/bin/env python3
"""
Debug API Response Structure
"""

import sys
import os
import json

# Add the main directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Main'))

from serpapi_client import SerpAPIFlightClient

def debug_api_response():
    """Debug what the API actually returns"""
    print("🔍 DEBUG: Testing API response structure...")
    
    # Get API key
    api_key = os.getenv('SERPAPI_KEY')
    if not api_key:
        print("❌ No API key found")
        return
    
    # Initialize API client
    client = SerpAPIFlightClient(api_key)
    
    # Make a simple test call
    print("\n🔍 Making test API call...")
    result = client.search_round_trip(
        departure_id="LAX",
        arrival_id="JFK",
        outbound_date="2025-12-20",
        return_date="2025-12-27",
        adults=1
    )
    
    print(f"\n📊 API Result Structure:")
    print(f"  Type: {type(result)}")
    print(f"  Keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
    
    if isinstance(result, dict):
        print(f"  Success: {result.get('success')}")
        print(f"  Search ID: {result.get('search_id')}")
        print(f"  Has 'data' key: {'data' in result}")
        
        # Check what's in the result
        for key, value in result.items():
            if key == 'data' and isinstance(value, dict):
                print(f"  data keys: {list(value.keys())}")
            elif key not in ['data']:
                print(f"  {key}: {type(value)} - {str(value)[:100]}...")

if __name__ == "__main__":
    debug_api_response()
