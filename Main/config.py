"""
Configuration settings for SerpAPI Flight Data System
"""

import os
from typing import Any

from dotenv import load_dotenv

# SerpAPI Configuration
SERPAPI_CONFIG = {
    'base_url': 'https://serpapi.com/search',
    'engine': 'google_flights',
    'api_key': None,  # Set via environment variable SERPAPI_KEY
    'timeout': 30,
    'max_retries': 3,
    'retry_delay': 1.0,
}

# Default search parameters
DEFAULT_SEARCH_PARAMS = {
    'currency': 'USD',
    'hl': 'en',
    'gl': 'us',
    'adults': 1,
    'children': 0,
    'infants_in_seat': 0,
    'infants_on_lap': 0,
    'travel_class': 3,  # Business (default changed from Economy)
    'type': 1,  # Round trip
    'deep_search': False,
    'show_hidden': False,
}

# Database configuration
DATABASE_CONFIG = {
    'db_path': 'DB/Main_DB.db',  # Fixed: relative from project root
    'backup_on_error': True,
    'connection_timeout': 30,
}

# Data processing configuration
PROCESSING_CONFIG = {
    'preserve_raw_data': True,
    'validate_data': True,
    'auto_extract_airports': True,
    'auto_extract_airlines': True,
    'calculate_analytics': True,
}

# Logging configuration
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    # Central logging actually uses core.logging_setup -> Main/logs/flight_system.log
    # Kept here only for validation tooling; do NOT point to removed Temp/ directory.
    'file_path': 'Main/logs/flight_system.log',
}

# Rate limiting configuration
RATE_LIMIT_CONFIG = {
    'requests_per_minute': 60,
    'requests_per_hour': 1000,
    'enable_rate_limiting': True,
}

# Validation rules
VALIDATION_RULES = {
    'airport_code_length': 3,
    'max_search_days_ahead': 365,
    'min_search_days_ahead': 1,
    'max_passengers': 9,
    'required_fields': ['departure_id', 'arrival_id', 'outbound_date'],
}

def get_api_key() -> str:
    """
    Get SerpAPI key from environment variable or .env file
    SECURITY: API keys should never be stored in plain text files
    """
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
    api_key = os.environ.get('SERPAPI_KEY')
    if not api_key:
        raise ValueError(
            "SERPAPI_KEY environment variable not set. "
            "Please set it in the .env file at the project root or as an environment variable."
        )
    return api_key

def validate_config() -> dict[str, Any]:
    """Validate configuration and return status"""
    issues = []
    
    # Check API key
    try:
        api_key = get_api_key()
    except ValueError:
        api_key = None
        
    if not api_key:
        issues.append("SERPAPI_KEY environment variable not set")
    
    # Check database path
    db_path = DATABASE_CONFIG['db_path']
    if not os.path.exists(db_path):
        issues.append(f"Database not found at {db_path}")
    
    # Check temp directory
    temp_dir = os.path.dirname(LOGGING_CONFIG['file_path'])
    if not os.path.exists(temp_dir):
        try:
            os.makedirs(temp_dir, exist_ok=True)
        except Exception as e:
            issues.append(f"Cannot create temp directory: {e}")
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'api_key_available': bool(api_key),
        'database_available': os.path.exists(db_path)
    }

if __name__ == "__main__":
    print("🔧 Configuration Validation")
    print("=" * 40)
    
    status = validate_config()
    
    if status['valid']:
        print("✅ Configuration is valid")
        print(f"🔑 API Key: {'Available' if status['api_key_available'] else 'Not Found'}")
        print(f"🗄️ Database: {'Available' if status['database_available'] else 'Not Found'}")
    else:
        print("❌ Configuration issues found:")
        for issue in status['issues']:
            print(f"   - {issue}")
    
    print(f"\n📊 Configuration Summary:")
    print(f"   - Base URL: {SERPAPI_CONFIG['base_url']}")
    print(f"   - Engine: {SERPAPI_CONFIG['engine']}")
    print(f"   - Default Currency: {DEFAULT_SEARCH_PARAMS['currency']}")
    print(f"   - Database Path: {DATABASE_CONFIG['db_path']}")
    print(f"   - Rate Limiting: {RATE_LIMIT_CONFIG['enable_rate_limiting']}")
