"""
Enhanced Flight Search Client with API Approval System
======================================================

This module wraps the existing flight search functionality with mandatory
API call approval to manage costs and usage.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, Any, Optional
from enhanced_flight_search import EnhancedFlightSearchClient
from api_approval_system import api_monitor, request_api_approval

class ApprovalRequiredFlightSearchClient:
    """Flight search client that requires approval for all API calls"""
    
    def __init__(self):
        self.base_client = EnhancedFlightSearchClient()
        self.pending_requests = {}
    
    def search_flights_with_approval(self, 
                                   departure_id: str,
                                   arrival_id: str,
                                   outbound_date: str,
                                   return_date: Optional[str] = None,
                                   reason: str = None,
                                   **kwargs) -> Dict[str, Any]:
        """
        Search for flights with mandatory approval process
        
        This method will:
        1. Check cache first (no approval needed)
        2. If cache miss, request approval for API call
        3. Return approval request for user decision
        """
        
        # Build search parameters
        search_params = {
            'departure_id': departure_id,
            'arrival_id': arrival_id,
            'outbound_date': outbound_date,
            'adults': kwargs.get('adults', 1),
            'children': kwargs.get('children', 0),
            'infants_in_seat': kwargs.get('infants_in_seat', 0),
            'infants_on_lap': kwargs.get('infants_on_lap', 0),
            'travel_class': kwargs.get('travel_class', 1),
            'currency': kwargs.get('currency', 'USD')
        }
        
        if return_date:
            search_params['return_date'] = return_date
        
        # Add engine for cost estimation
        search_params['engine'] = 'google_flights'
        
        # First, try cache-only search
        print("🔍 Checking local cache first...")
        cache_result = self.base_client.search_flights(
            force_api=False,
            max_cache_age_hours=kwargs.get('max_cache_age_hours', 24),
            **search_params
        )
        
        # If cache hit, return immediately
        if cache_result.get('success') and cache_result.get('source') == 'cache':
            cache_result['approval_required'] = False
            cache_result['approval_reason'] = 'Data found in cache - no API call needed'
            return cache_result
        
        # Cache miss - need API approval
        print("❌ Cache miss - API call required")
        
        # Generate reason if not provided
        if not reason:
            route = f"{departure_id} to {arrival_id}"
            date_info = f"on {outbound_date}"
            if return_date:
                date_info += f" returning {return_date}"
            reason = f"Flight search: {route} {date_info}"
        
        # Request approval
        should_proceed, approval_request = request_api_approval(search_params, reason)
        
        # Store the request for later approval
        self.pending_requests[approval_request.search_id] = {
            'request': approval_request,
            'search_params': search_params,
            'kwargs': kwargs
        }
        
        return {
            'success': False,
            'approval_required': True,
            'approval_request_id': approval_request.search_id,
            'estimated_cost': approval_request.estimated_cost,
            'message': 'API call approval required - use approve_and_execute() to proceed',
            'source': 'approval_pending'
        }
    
    def approve_and_execute(self, request_id: str) -> Dict[str, Any]:
        """Approve and execute a pending API request"""
        
        if request_id not in self.pending_requests:
            return {
                'success': False,
                'error': f'No pending request found with ID: {request_id}',
                'source': 'approval_error'
            }
        
        pending = self.pending_requests[request_id]
        approval_request = pending['request']
        search_params = pending['search_params']
        kwargs = pending['kwargs']
        
        # Approve the request
        if not api_monitor.approve_request(approval_request):
            return {
                'success': False,
                'error': 'Failed to approve request',
                'source': 'approval_error'
            }
        
        print(f"✅ Request {request_id} approved - executing API call...")
        
        # Remove engine from search params (not needed for actual search)
        search_params_clean = {k: v for k, v in search_params.items() if k != 'engine'}
        
        # Execute the actual search with force_api=True
        try:
            result = self.base_client.search_flights(
                force_api=True,  # Force API call since we approved it
                **search_params_clean,
                **kwargs
            )
            
            # Add approval information to result
            result['approval_request_id'] = request_id
            result['approved_cost'] = approval_request.estimated_cost
            
            # Clean up pending request
            del self.pending_requests[request_id]
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'API call failed after approval: {str(e)}',
                'source': 'api_error',
                'approval_request_id': request_id
            }
    
    def reject_request(self, request_id: str, reason: str = "User declined") -> Dict[str, Any]:
        """Reject a pending API request"""
        
        if request_id not in self.pending_requests:
            return {
                'success': False,
                'error': f'No pending request found with ID: {request_id}',
                'source': 'approval_error'
            }
        
        pending = self.pending_requests[request_id]
        approval_request = pending['request']
        
        # Reject the request
        if api_monitor.reject_request(approval_request, reason):
            del self.pending_requests[request_id]
            return {
                'success': True,
                'message': f'Request {request_id} rejected: {reason}',
                'source': 'approval_rejected'
            }
        else:
            return {
                'success': False,
                'error': 'Failed to reject request',
                'source': 'approval_error'
            }
    
    def get_pending_requests(self) -> Dict[str, Any]:
        """Get all pending approval requests"""
        return {
            request_id: {
                'search_id': data['request'].search_id,
                'estimated_cost': data['request'].estimated_cost,
                'call_type': data['request'].call_type,
                'reason': data['request'].reason,
                'timestamp': data['request'].timestamp
            }
            for request_id, data in self.pending_requests.items()
        }
    
    def get_usage_report(self) -> str:
        """Get current API usage report"""
        return api_monitor.generate_usage_report()

def demo_approval_workflow():
    """Demonstrate the approval workflow"""
    print("🧪 DEMO: API Approval Workflow")
    print("=" * 50)
    
    client = ApprovalRequiredFlightSearchClient()
    
    # Test search that will require approval
    print("\n1. Testing flight search with approval requirement...")
    result = client.search_flights_with_approval(
        departure_id='POM',
        arrival_id='MNL',
        outbound_date='2025-09-26',
        reason='Demo flight search for approval system'
    )
    
    print(f"Result: {result}")
    
    if result.get('approval_required'):
        request_id = result['approval_request_id']
        print(f"\n2. Got approval request: {request_id}")
        print(f"   Estimated cost: ${result['estimated_cost']:.4f}")
        
        # Show pending requests
        pending = client.get_pending_requests()
        print(f"\n3. Pending requests: {len(pending)}")
        
        print("\n4. To approve and execute:")
        print(f"   client.approve_and_execute('{request_id}')")
        
        print("\n5. To reject:")
        print(f"   client.reject_request('{request_id}', 'Not needed')")
    
    # Show usage report
    print("\n" + "=" * 50)
    print("USAGE REPORT:")
    print(client.get_usage_report())

if __name__ == "__main__":
    demo_approval_workflow()
