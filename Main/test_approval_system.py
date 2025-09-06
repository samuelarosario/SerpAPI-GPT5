"""
API Approval System Test
========================

This script demonstrates the complete API approval workflow for SerpAPI calls.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from approved_flight_search import ApprovalRequiredFlightSearchClient

def test_approval_system():
    """Test the complete approval system workflow"""
    
    print("🔍 SerpAPI CALL APPROVAL SYSTEM TEST")
    print("=" * 60)
    
    # Initialize the approval-required client
    client = ApprovalRequiredFlightSearchClient()
    
    print("\n📊 Current Usage Statistics:")
    print(client.get_usage_report())
    
    print("\n" + "=" * 60)
    print("🧪 TESTING: Flight Search with Approval Requirement")
    print("=" * 60)
    
    # Test 1: Search that may hit cache (no approval needed)
    print("\n1️⃣  First Search - Checking Cache...")
    result1 = client.search_flights_with_approval(
        departure_id='POM',
        arrival_id='MNL', 
        outbound_date='2025-09-26',
        reason='Test search 1 - may use cache'
    )
    
    print(f"   ✅ Success: {result1.get('success')}")
    print(f"   📍 Source: {result1.get('source')}")
    print(f"   🔐 Approval Required: {result1.get('approval_required', False)}")
    
    if result1.get('approval_required'):
        request_id_1 = result1['approval_request_id']
        print(f"   🆔 Request ID: {request_id_1}")
        print(f"   💰 Estimated Cost: ${result1['estimated_cost']:.4f}")
        
        # Show what approval would look like
        print(f"\n   ⚠️  This search requires approval!")
        print(f"   ➡️  To approve: client.approve_and_execute('{request_id_1}')")
        print(f"   ➡️  To reject: client.reject_request('{request_id_1}')")
    
    print(f"   📝 Message: {result1.get('message', 'No message')}")
    
    # Test 2: Different route search (likely to require approval)
    print("\n2️⃣  Second Search - Different Route...")
    result2 = client.search_flights_with_approval(
        departure_id='LAX',
        arrival_id='JFK',
        outbound_date='2025-10-15',
        return_date='2025-10-22',
        reason='Test search 2 - round trip domestic US'
    )
    
    print(f"   ✅ Success: {result2.get('success')}")
    print(f"   📍 Source: {result2.get('source')}")
    print(f"   🔐 Approval Required: {result2.get('approval_required', False)}")
    
    if result2.get('approval_required'):
        request_id_2 = result2['approval_request_id']
        print(f"   🆔 Request ID: {request_id_2}")
        print(f"   💰 Estimated Cost: ${result2['estimated_cost']:.4f}")
    
    # Show all pending requests
    print("\n📋 PENDING APPROVAL REQUESTS:")
    print("-" * 40)
    pending = client.get_pending_requests()
    
    if pending:
        for req_id, details in pending.items():
            print(f"   🆔 ID: {req_id}")
            print(f"   💰 Cost: ${details['estimated_cost']:.4f}")
            print(f"   📝 Reason: {details['reason']}")
            print(f"   🕐 Time: {details['timestamp']}")
            print(f"   🔧 Type: {details['call_type']}")
            print("   " + "-" * 35)
    else:
        print("   ✅ No pending requests")
    
    # Show updated usage statistics
    print("\n📊 UPDATED USAGE STATISTICS:")
    print(client.get_usage_report())
    
    print("\n" + "=" * 60)
    print("🎯 NEXT STEPS:")
    print("=" * 60)
    
    if pending:
        print("\n⚠️  You have pending API call requests that require approval!")
        print("\n🔐 TO APPROVE AND EXECUTE:")
        for req_id in pending.keys():
            print(f"   client.approve_and_execute('{req_id}')")
        
        print("\n❌ TO REJECT:")
        for req_id in pending.keys():
            print(f"   client.reject_request('{req_id}', 'Reason for rejection')")
        
        print("\n📝 USAGE:")
        print("   1. Review the approval requests above")
        print("   2. Check estimated costs and reasons")
        print("   3. Use approve_and_execute() to proceed with API calls")
        print("   4. Use reject_request() to decline API calls")
        
    else:
        print("\n✅ No approval required - all searches used cached data!")
    
    return pending

def approve_all_demo(client, pending_requests):
    """Demo function to approve all pending requests"""
    if not pending_requests:
        print("❌ No pending requests to approve")
        return
    
    print("\n🚀 DEMO: Approving All Pending Requests")
    print("=" * 50)
    
    for req_id in pending_requests.keys():
        print(f"\n✅ Approving request: {req_id}")
        result = client.approve_and_execute(req_id)
        
        print(f"   Success: {result.get('success')}")
        print(f"   Source: {result.get('source')}")
        
        if result.get('success'):
            data = result.get('data', {})
            if 'best_flights' in data:
                flights = data['best_flights']
                print(f"   Found {len(flights)} flight options")
                if flights:
                    cheapest = min(flights, key=lambda x: x.get('price', float('inf')))
                    print(f"   Cheapest: ${cheapest.get('price', 'N/A')} ({cheapest.get('flights', [{}])[0].get('airline', 'Unknown')})")
        else:
            print(f"   Error: {result.get('error', 'Unknown error')}")
    
    print(f"\n📊 Final Usage Report:")
    print(client.get_usage_report())

if __name__ == "__main__":
    # Run the test
    pending_requests = test_approval_system()
    
    # Ask if user wants to see the approval demo
    print("\n" + "=" * 60)
    print("💡 INTERACTIVE DEMO AVAILABLE")
    print("=" * 60)
    print("\nThis test has generated approval requests but hasn't executed them.")
    print("The requests are pending your approval.")
    print("\nTo see the full workflow including execution:")
    print("1. Run this script")
    print("2. Note the pending request IDs")
    print("3. Use client.approve_and_execute(request_id) for each one")
    print("\nOr uncomment the line below to auto-approve all requests:")
    print("# approve_all_demo(client, pending_requests)")
