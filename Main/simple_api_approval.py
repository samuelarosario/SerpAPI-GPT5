"""
Simple API Approval Prompt System
=================================

This module provides a simple prompt-based approval system for API calls.
No complex pending request management - just immediate approve/decline prompts.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Tuple
import hashlib

class SimpleAPIApproval:
    """Simple API approval with immediate prompts"""
    
    def __init__(self, log_file: str = "api_calls.log"):
        self.log_file = log_file
        self.logger = self._setup_logging()
        self.calls_today = self._load_todays_calls()
        
        # API cost estimates (USD per search)
        self.cost_estimates = {
            'flights': 0.05,
            'hotels': 0.05,
            'general': 0.01
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for API calls"""
        logger = logging.getLogger('api_approval')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.FileHandler(self.log_file)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _load_todays_calls(self) -> list:
        """Load today's API calls for usage tracking"""
        calls = []
        if not os.path.exists(self.log_file):
            return calls
        
        today = datetime.now().date()
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    if ' - INFO - ' in line:
                        try:
                            call_data = json.loads(line.split(' - INFO - ')[1])
                            call_date = datetime.fromisoformat(call_data['timestamp']).date()
                            if call_date == today and call_data.get('status') == 'approved':
                                calls.append(call_data)
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
        except Exception:
            pass
        
        return calls
    
    def _estimate_cost(self, search_params: Dict[str, Any]) -> float:
        """Estimate cost for a search"""
        engine = search_params.get('engine', 'general')
        if 'flights' in engine:
            return self.cost_estimates['flights']
        elif 'hotels' in engine:
            return self.cost_estimates['hotels']
        else:
            return self.cost_estimates['general']
    
    def _get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        total_calls = len(self.calls_today)
        total_cost = sum(call.get('estimated_cost', 0) for call in self.calls_today)
        
        return {
            'total_calls': total_calls,
            'total_cost_usd': round(total_cost, 4)
        }
    
    def prompt_for_approval(self, search_params: Dict[str, Any], reason: str = "API call") -> bool:
        """
        Display API call details and prompt for immediate approval
        Returns True if approved, False if declined
        """
        
        # Generate search ID for logging
        param_string = json.dumps(search_params, sort_keys=True)
        search_hash = hashlib.md5(param_string.encode()).hexdigest()[:12]
        search_id = f"search_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{search_hash}"
        
        # Calculate costs
        estimated_cost = self._estimate_cost(search_params)
        stats = self._get_usage_stats()
        new_total_cost = stats['total_cost_usd'] + estimated_cost
        
        # Determine call type
        engine = search_params.get('engine', 'unknown')
        call_type = 'flights' if 'flights' in engine else engine
        
        # Display the approval prompt
        print("\n" + "="*70)
        print("🔍 API CALL APPROVAL REQUIRED")
        print("="*70)
        print(f"📋 Reason: {reason}")
        print(f"🔧 Type: {call_type}")
        print(f"💰 Cost: ${estimated_cost:.4f} USD")
        print(f"📊 Today's usage: {stats['total_calls']} calls, ${stats['total_cost_usd']:.4f}")
        print(f"📈 New total: ${new_total_cost:.4f} USD")
        print()
        
        # Show key parameters (hide sensitive data)
        print("🔧 Search Parameters:")
        for key, value in search_params.items():
            if key not in ['api_key', 'engine']:  # Hide sensitive/internal params
                print(f"   {key}: {value}")
        
        print("="*70)
        
        # Get user input
        while True:
            response = input("⚠️  Proceed with API call? (y/yes/n/no): ").lower().strip()
            
            if response in ['y', 'yes']:
                # Log the approval
                call_log = {
                    'search_id': search_id,
                    'timestamp': datetime.now().isoformat(),
                    'call_type': call_type,
                    'estimated_cost': estimated_cost,
                    'reason': reason,
                    'status': 'approved',
                    'search_params': {k: v for k, v in search_params.items() if k != 'api_key'}
                }
                
                self.logger.info(json.dumps(call_log))
                self.calls_today.append(call_log)
                
                print("✅ API call approved - proceeding...")
                return True
                
            elif response in ['n', 'no']:
                # Log the rejection
                rejection_log = {
                    'search_id': search_id,
                    'timestamp': datetime.now().isoformat(),
                    'call_type': call_type,
                    'estimated_cost': estimated_cost,
                    'reason': reason,
                    'status': 'rejected'
                }
                
                self.logger.info(json.dumps(rejection_log))
                
                print("❌ API call declined")
                return False
                
            else:
                print("Please enter 'y' or 'yes' to approve, 'n' or 'no' to decline")

# Global approval instance
api_approval = SimpleAPIApproval()

def require_approval(search_params: Dict[str, Any], reason: str = "API call") -> bool:
    """
    Simple function to require approval for API calls
    Returns True if approved, False if declined
    """
    return api_approval.prompt_for_approval(search_params, reason)

# Test function
def test_approval_prompt():
    """Test the approval prompt"""
    print("🧪 Testing API Approval Prompt...")
    
    test_params = {
        'engine': 'google_flights',
        'departure_id': 'POM',
        'arrival_id': 'MNL',
        'outbound_date': '2025-09-26',
        'currency': 'USD'
    }
    
    approved = require_approval(test_params, "Test flight search POM to MNL")
    print(f"Result: {'Approved' if approved else 'Declined'}")

if __name__ == "__main__":
    test_approval_prompt()
