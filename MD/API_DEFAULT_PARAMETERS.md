# SerpAPI Default Configuration Parameters

## 🔧 **API Endpoint Configuration**

### **Base API Settings**
- **Base URL**: `https://serpapi.com/search`
- **Engine**: `google_flights`
- **Timeout**: 30 seconds
- **Max Retries**: 3 attempts
- **Retry Delay**: 1.0 seconds

### **Authentication**
- **API Key**: Retrieved from environment variable `SERPAPI_KEY`
- **Security**: No hardcoded keys (environment variable only)

## 📋 **Default Search Parameters**

The system uses these default parameters for all flight searches:

### **Localization & Currency**
```python
DEFAULT_SEARCH_PARAMS = {
    'currency': 'USD',          # United States Dollar
    'hl': 'en',                # Language: English
    'gl': 'us',                # Country: United States
}
```

### **Passenger Configuration**
```python
{
    'adults': 1,               # Number of adult passengers
    'children': 0,             # Number of child passengers (2-11 years)
    'infants_in_seat': 0,      # Number of infants with seats (<2 years)
    'infants_on_lap': 0,       # Number of lap infants (<2 years)
}
```

### **Flight Type & Class**
```python
{
    'travel_class': 3,         # DEFAULT NOW Business (1=Economy, 2=Premium, 3=Business, 4=First)
    'type': 1,                 # 1=Round trip, 2=One way, 3=Multi-city
}
```

### **Search Options**
```python
{
    'deep_search': False,      # Faster results vs comprehensive search
    'show_hidden': False,      # Include hidden/budget carriers
}
```

## 🎯 **Enhanced Search Behavior**

### **Automatic Return Date Generation**
- If no return date is provided for round-trip searches
- **Default**: 7 days after outbound date
- **Purpose**: Capture more comprehensive pricing data

### **Cache Settings**
- **Max Age**: 24 hours (data freshness requirement)
- **Auto Cleanup**: Data older than 7 days (168 hours)

## 🛡️ **Rate Limiting**
```python
RATE_LIMIT_CONFIG = {
    'requests_per_minute': 60,
    'requests_per_hour': 1000,
    'enable_rate_limiting': True,
}
```

## ✅ **Validation Rules**
```python
VALIDATION_RULES = {
    'airport_code_length': 3,        # IATA codes must be 3 characters
    'max_search_days_ahead': 365,    # Can search up to 1 year ahead
    'min_search_days_ahead': 1,      # Must be at least 1 day ahead
    'max_passengers': 9,             # Maximum total passengers
    'required_fields': [             # Mandatory search parameters
        'departure_id', 
        'arrival_id', 
        'outbound_date'
    ],
}
```

## 📊 **Parameter Override**

### **How Defaults Are Applied**
1. **Base defaults** loaded from `DEFAULT_SEARCH_PARAMS`
2. **User parameters** override defaults via `kwargs`
3. **Required API parameters** added (engine, api_key)
4. **None values** filtered out

### **Example Override**
```python
# Default: business class, 1 adult, USD
client.search_flights(
    departure_id="POM",
    arrival_id="MNL", 
    outbound_date="2025-09-26",
    adults=2,              # Override: 2 passengers
    travel_class=3,        # Override: Business class
    currency="AUD"         # Override: Australian Dollars
)
```

## 🗄️ **Database Configuration**
```python
DATABASE_CONFIG = {
    'db_path': '../DB/Main_DB.db',
    'backup_on_error': True,
    'connection_timeout': 30,
}
```

## 📈 **Processing Configuration**
```python
PROCESSING_CONFIG = {
    'preserve_raw_data': True,      # Keep original API responses
    'validate_data': True,          # Validate before storage
    'auto_extract_airports': True,  # Extract airport data (now centralized)
    'auto_extract_airlines': True,  # Extract airline data
    'calculate_analytics': True,    # Generate route analytics
}
```

---

## 🎯 **Summary**

The system is configured for **US-based searches** with **business class** preferences by default, optimized for **comprehensive data capture** with **24-hour cache freshness** and **proper rate limiting** to respect API quotas.

All parameters can be overridden on a per-search basis while maintaining sensible defaults for routine operations.
