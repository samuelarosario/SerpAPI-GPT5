"""
Demo: Simple API Approval Prompt
================================

This script shows what the approval prompt looks like without making actual API calls.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from simple_api_approval import require_approval

def demo_approval_prompts():
    """Demonstrate what the approval prompts look like"""
    
    print("🎯 DEMONSTRATION: API Approval Prompts")
    print("=" * 60)
    print("This shows what you'll see when API calls need approval.")
    print("In actual use, you would type 'y' to approve or 'n' to decline.")
    print()
    
    # Demo 1: POM to MNL flight search
    print("📋 EXAMPLE 1: Single flight search")
    print("-" * 40)
    
    demo_params_1 = {
        'engine': 'google_flights',
        'departure_id': 'POM',
        'arrival_id': 'MNL',
        'outbound_date': '2025-09-26',
        'adults': 1,
        'currency': 'USD'
    }
    
    print("This is what you would see for a POM → MNL flight search:")
    print()
    
    # Show the approval prompt (but don't actually wait for input in demo)
    # We'll simulate by calling the internal methods
    from simple_api_approval import api_approval
    
    # Calculate what would be shown
    estimated_cost = api_approval._estimate_cost(demo_params_1)
    stats = api_approval._get_usage_stats()
    new_total_cost = stats['total_cost_usd'] + estimated_cost
    call_type = 'flights'
    reason = "Flight search: POM → MNL on 2025-09-26"
    
    # Display what the prompt would look like
    print("="*70)
    print("🔍 API CALL APPROVAL REQUIRED")
    print("="*70)
    print(f"📋 Reason: {reason}")
    print(f"🔧 Type: {call_type}")
    print(f"💰 Cost: ${estimated_cost:.4f} USD")
    print(f"📊 Today's usage: {stats['total_calls']} calls, ${stats['total_cost_usd']:.4f}")
    print(f"📈 New total: ${new_total_cost:.4f} USD")
    print()
    print("🔧 Search Parameters:")
    for key, value in demo_params_1.items():
        if key not in ['api_key', 'engine']:
            print(f"   {key}: {value}")
    print("="*70)
    print("⚠️  Proceed with API call? (y/yes/n/no): [DEMO - NO INPUT REQUIRED]")
    print()
    
    print("✅ In real use, you would type 'y' to approve or 'n' to decline")
    print()
    
    # Demo 2: Round trip search
    print("📋 EXAMPLE 2: Round-trip flight search")
    print("-" * 40)
    
    demo_params_2 = {
        'engine': 'google_flights',
        'departure_id': 'LAX',
        'arrival_id': 'JFK',
        'outbound_date': '2025-10-15',
        'return_date': '2025-10-22',
        'adults': 2,
        'children': 1,
        'currency': 'USD'
    }
    
    # Calculate for second example
    estimated_cost_2 = api_approval._estimate_cost(demo_params_2)
    reason_2 = "Flight search: LAX → JFK on 2025-10-15 (return 2025-10-22)"
    
    print("This is what you would see for a LAX → JFK round-trip search:")
    print()
    print("="*70)
    print("🔍 API CALL APPROVAL REQUIRED")
    print("="*70)
    print(f"📋 Reason: {reason_2}")
    print(f"🔧 Type: flights")
    print(f"💰 Cost: ${estimated_cost_2:.4f} USD")
    print(f"📊 Today's usage: {stats['total_calls']} calls, ${stats['total_cost_usd']:.4f}")
    print(f"📈 New total: ${stats['total_cost_usd'] + estimated_cost_2:.4f} USD")
    print()
    print("🔧 Search Parameters:")
    for key, value in demo_params_2.items():
        if key not in ['api_key', 'engine']:
            print(f"   {key}: {value}")
    print("="*70)
    print("⚠️  Proceed with API call? (y/yes/n/no): [DEMO - NO INPUT REQUIRED]")
    print()
    
    print("✅ In real use, you would type 'y' to approve or 'n' to decline")
    print()
    
    print("🎯 KEY FEATURES:")
    print("=" * 30)
    print("✅ Immediate prompt - no complex pending system")
    print("✅ Clear cost information shown upfront")
    print("✅ Simple y/n response required")
    print("✅ All calls logged for tracking")
    print("✅ Cache checked first - only prompts when API needed")
    print("✅ Usage statistics shown with each prompt")
    
    print("\n🚀 READY TO USE:")
    print("The system is now integrated into your flight search client.")
    print("Every API call will show a prompt like the examples above.")
    print("Simply respond with 'y' to proceed or 'n' to cancel.")

if __name__ == "__main__":
    demo_approval_prompts()
