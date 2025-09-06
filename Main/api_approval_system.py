"""
SerpAPI Call Monitor and Approval System
========================================

This module monitors all SerpAPI calls, tracks usage, and requests user approval
before making API requests to manage costs and rate limits.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import hashlib

@dataclass
class APICallRequest:
    """Represents a pending API call request"""
    search_params: Dict[str, Any]
    estimated_cost: float
    call_type: str
    timestamp: str
    search_id: str
    reason: str
    
class APICallMonitor:
    """Monitors and manages SerpAPI calls with approval workflow"""
    
    def __init__(self, log_file: str = "api_calls.log"):
        self.log_file = log_file
        self.logger = self._setup_logging()
        self.calls_today = []
        self.pending_requests = []
        
        # API cost estimates (USD per search)
        self.cost_estimates = {
            'flights': 0.05,  # $0.05 per flight search
            'hotels': 0.05,   # $0.05 per hotel search
            'general': 0.01   # $0.01 per general search
        }
        
        # Load existing call history
        self._load_call_history()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for API calls"""
        logger = logging.getLogger('api_monitor')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.FileHandler(self.log_file)
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _load_call_history(self):
        """Load today's API call history"""
        if not os.path.exists(self.log_file):
            return
        
        today = datetime.now().date()
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            call_data = json.loads(line.split(' - INFO - ')[1])
                            call_date = datetime.fromisoformat(call_data['timestamp']).date()
                            if call_date == today:
                                self.calls_today.append(call_data)
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
        except Exception as e:
            self.logger.error(f"Failed to load call history: {e}")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        today = datetime.now().date()
        
        # Filter today's calls
        today_calls = [call for call in self.calls_today 
                      if datetime.fromisoformat(call['timestamp']).date() == today]
        
        total_calls = len(today_calls)
        total_cost = sum(call.get('estimated_cost', 0) for call in today_calls)
        
        # Group by call type
        by_type = {}
        for call in today_calls:
            call_type = call.get('call_type', 'unknown')
            if call_type not in by_type:
                by_type[call_type] = {'count': 0, 'cost': 0}
            by_type[call_type]['count'] += 1
            by_type[call_type]['cost'] += call.get('estimated_cost', 0)
        
        return {
            'date': today.isoformat(),
            'total_calls': total_calls,
            'total_cost_usd': round(total_cost, 4),
            'by_type': by_type,
            'pending_requests': len(self.pending_requests)
        }
    
    def estimate_cost(self, search_params: Dict[str, Any]) -> float:
        """Estimate cost for a search based on parameters"""
        engine = search_params.get('engine', 'general')
        
        if 'flights' in engine:
            return self.cost_estimates['flights']
        elif 'hotels' in engine:
            return self.cost_estimates['hotels']
        else:
            return self.cost_estimates['general']
    
    def create_approval_request(self, 
                              search_params: Dict[str, Any],
                              reason: str = "Flight search request") -> APICallRequest:
        """Create an API call approval request"""
        
        # Generate search ID
        param_string = json.dumps(search_params, sort_keys=True)
        search_hash = hashlib.md5(param_string.encode()).hexdigest()[:12]
        timestamp = datetime.now().isoformat()
        search_id = f"search_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{search_hash}"
        
        # Estimate cost
        estimated_cost = self.estimate_cost(search_params)
        
        # Determine call type
        engine = search_params.get('engine', 'unknown')
        call_type = 'flights' if 'flights' in engine else engine
        
        request = APICallRequest(
            search_params=search_params,
            estimated_cost=estimated_cost,
            call_type=call_type,
            timestamp=timestamp,
            search_id=search_id,
            reason=reason
        )
        
        self.pending_requests.append(request)
        return request
    
    def display_approval_request(self, request: APICallRequest) -> str:
        """Format approval request for display"""
        
        # Get current usage stats
        stats = self.get_usage_stats()
        
        # Calculate new totals if approved
        new_total_calls = stats['total_calls'] + 1
        new_total_cost = stats['total_cost_usd'] + request.estimated_cost
        
        output = []
        output.append("=" * 70)
        output.append("🔍 SerpAPI CALL APPROVAL REQUEST")
        output.append("=" * 70)
        output.append("")
        
        # Request details
        output.append("📋 REQUEST DETAILS:")
        output.append(f"   Search ID: {request.search_id}")
        output.append(f"   Reason: {request.reason}")
        output.append(f"   Call Type: {request.call_type}")
        output.append(f"   Timestamp: {request.timestamp}")
        output.append("")
        
        # Search parameters
        output.append("🔧 SEARCH PARAMETERS:")
        for key, value in request.search_params.items():
            if key != 'api_key':  # Don't show API key
                output.append(f"   {key}: {value}")
        output.append("")
        
        # Cost information
        output.append("💰 COST ANALYSIS:")
        output.append(f"   Estimated Cost: ${request.estimated_cost:.4f} USD")
        output.append(f"   Current Today's Cost: ${stats['total_cost_usd']:.4f} USD")
        output.append(f"   New Total (if approved): ${new_total_cost:.4f} USD")
        output.append("")
        
        # Usage statistics
        output.append("📊 TODAY'S USAGE STATISTICS:")
        output.append(f"   Total Calls: {stats['total_calls']}")
        output.append(f"   New Total (if approved): {new_total_calls}")
        output.append("")
        
        if stats['by_type']:
            output.append("   By Type:")
            for call_type, data in stats['by_type'].items():
                output.append(f"     {call_type}: {data['count']} calls, ${data['cost']:.4f}")
        
        output.append("")
        output.append("⚠️  APPROVAL REQUIRED:")
        output.append("   This API call requires your approval before execution.")
        output.append("   Please review the details above and confirm if you want to proceed.")
        output.append("")
        output.append("=" * 70)
        
        return "\n".join(output)
    
    def approve_request(self, request: APICallRequest) -> bool:
        """Approve and log an API request"""
        try:
            # Remove from pending
            if request in self.pending_requests:
                self.pending_requests.remove(request)
            
            # Log the approved call
            call_log = {
                'search_id': request.search_id,
                'timestamp': request.timestamp,
                'call_type': request.call_type,
                'estimated_cost': request.estimated_cost,
                'reason': request.reason,
                'status': 'approved',
                'search_params': {k: v for k, v in request.search_params.items() 
                                if k != 'api_key'}  # Don't log API key
            }
            
            self.logger.info(json.dumps(call_log))
            self.calls_today.append(call_log)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to approve request {request.search_id}: {e}")
            return False
    
    def reject_request(self, request: APICallRequest, reason: str = "User declined") -> bool:
        """Reject an API request"""
        try:
            # Remove from pending
            if request in self.pending_requests:
                self.pending_requests.remove(request)
            
            # Log the rejection
            rejection_log = {
                'search_id': request.search_id,
                'timestamp': request.timestamp,
                'call_type': request.call_type,
                'estimated_cost': request.estimated_cost,
                'reason': request.reason,
                'status': 'rejected',
                'rejection_reason': reason
            }
            
            self.logger.info(json.dumps(rejection_log))
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reject request {request.search_id}: {e}")
            return False
    
    def get_pending_requests(self) -> List[APICallRequest]:
        """Get all pending approval requests"""
        return self.pending_requests.copy()
    
    def clear_old_requests(self, hours: int = 24):
        """Clear old pending requests"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        self.pending_requests = [
            req for req in self.pending_requests
            if datetime.fromisoformat(req.timestamp) > cutoff
        ]
    
    def generate_usage_report(self) -> str:
        """Generate a detailed usage report"""
        stats = self.get_usage_stats()
        
        output = []
        output.append("📊 SerpAPI USAGE REPORT")
        output.append("=" * 50)
        output.append(f"Date: {stats['date']}")
        output.append(f"Total Calls: {stats['total_calls']}")
        output.append(f"Total Cost: ${stats['total_cost_usd']:.4f} USD")
        output.append("")
        
        if stats['by_type']:
            output.append("Breakdown by Type:")
            for call_type, data in stats['by_type'].items():
                output.append(f"  {call_type}:")
                output.append(f"    Calls: {data['count']}")
                output.append(f"    Cost: ${data['cost']:.4f}")
            output.append("")
        
        output.append(f"Pending Requests: {stats['pending_requests']}")
        output.append("=" * 50)
        
        return "\n".join(output)

# Global monitor instance
api_monitor = APICallMonitor()

def request_api_approval(search_params: Dict[str, Any], 
                        reason: str = "API call request") -> Tuple[bool, Optional[APICallRequest]]:
    """
    Request approval for an API call
    
    Returns:
        Tuple of (should_proceed, request_object)
    """
    
    # Create approval request
    request = api_monitor.create_approval_request(search_params, reason)
    
    # Display the request
    approval_text = api_monitor.display_approval_request(request)
    print(approval_text)
    
    # Return the request for manual approval
    return False, request

if __name__ == "__main__":
    # Test the monitor
    test_params = {
        'engine': 'google_flights',
        'departure_id': 'POM',
        'arrival_id': 'MNL',
        'outbound_date': '2025-09-26',
        'currency': 'USD'
    }
    
    should_proceed, request = request_api_approval(test_params, "Test flight search")
    print(f"Should proceed: {should_proceed}")
    print(f"Request ID: {request.search_id if request else 'None'}")
    
    # Show usage report
    print("\n" + api_monitor.generate_usage_report())
