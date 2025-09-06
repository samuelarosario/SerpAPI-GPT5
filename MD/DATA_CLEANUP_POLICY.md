# Data Freshness and Cleanup Policy

## ❌ **NO - Tables Are NOT Reset Daily**

The system uses a **24-hour rolling cleanup policy** rather than complete daily resets. Here's how it actually works:

## 🔄 **24-Hour Rolling Data Policy**

### **What Gets Cleaned vs What Stays:**

**🗑️ CLEANED AUTOMATICALLY (24-hour rolling):**
- `flight_searches` - Search queries and parameters
- `flight_results` - Individual flight options and pricing  
- `flight_segments` - Flight legs and routing details
- `layovers` - Connection information
- `price_insights` - Pricing analysis data
- `api_queries` - Raw API response data

**💾 PERMANENT DATA (Never cleaned):**
- `airports` - Airport reference data (codes, names, locations)
- `airlines` - Airline reference data (codes, names, logos)
- `route_analytics` - Long-term route statistics and trends

## ⏰ **When Cleanup Happens**

### **Automatic Cleanup Triggers:**
```python
# Before every search operation
self.cache.cleanup_old_data(max_cache_age_hours=24)
```

**Cleanup runs:**
- ✅ **Before each new search** - Ensures fresh data window
- ✅ **Automatically** - No manual intervention needed
- ✅ **Intelligent** - Only removes data older than 24 hours

### **Current Status Example:**
```
📊 DATA IN YOUR DATABASE:
   Search ID | Route | Date | Created | Age(hrs)
   9aab4090 | POM→MNL | 2025-09-27 | 15:50 | 9.8h
   04bcbf5e | POM→MNL | 2025-09-26 | 15:47 | 9.7h
   04bcbf5e | POM→MNL | 2025-09-26 | 12:31 | 6.5h

✅ Status: ALL DATA FRESH (no cleanup needed)
```

## 🔧 **How the Cleanup Process Works**

### **Cascading Deletion Order:**
```sql
1. DELETE FROM layovers WHERE flight_result_id IN (old_searches)
2. DELETE FROM flight_segments WHERE flight_result_id IN (old_searches)  
3. DELETE FROM flight_results WHERE search_id IN (old_searches)
4. DELETE FROM price_insights WHERE search_id IN (old_searches)
5. DELETE FROM flight_searches WHERE created_at < cutoff_time
6. DELETE FROM api_queries WHERE created_at < cutoff_time
```

### **Foreign Key Protection:**
- Deletion follows **proper order** to respect foreign key constraints
- **Reference tables preserved** (airports, airlines)
- **Orphaned records prevented**

## 📈 **Cache Behavior Timeline**

```
Hour 0:  🔍 New search → API call → Store in DB
Hour 1:  💾 Same search → Cache hit → Instant response  
Hour 12: 💾 Same search → Cache hit → Instant response
Hour 23: 💾 Same search → Cache hit → Instant response
Hour 25: 🔍 Same search → API call → Old data cleaned, new data stored
```

## 🎯 **Key Benefits of Rolling Cleanup**

### **vs Daily Reset:**
- ✅ **Continuous availability** - No downtime periods
- ✅ **Efficient storage** - Only keeps relevant recent data
- ✅ **Better performance** - Smaller database size
- ✅ **Cost optimization** - Prevents redundant API calls within 24h

### **vs Permanent Storage:**
- ✅ **Fresh pricing** - Flight prices change rapidly
- ✅ **Current schedules** - Flight times and availability change
- ✅ **Storage efficiency** - Database doesn't grow indefinitely
- ✅ **Privacy compliance** - Search history is temporary

## 📊 **Data Lifecycle Summary**

```
Reference Data (Permanent):
├── Airports: JFK, LAX, POM, MNL... ♾️
└── Airlines: QF, AA, UA, PR... ♾️

Flight Data (24-hour rolling):
├── Search: POM→MNL on 2025-09-27 ⏰ 24h
├── Results: $1,391, $2,396... ⏰ 24h  
├── Segments: QF58, QF97... ⏰ 24h
└── Cache: Hash keys and responses ⏰ 24h
```

## 💡 **Why This Design is Optimal**

1. **🔄 Fresh Data**: Flight prices and schedules change frequently
2. **💰 Cost Control**: Prevents unnecessary API calls within 24h window  
3. **⚡ Performance**: Smaller, cleaner database with better query speeds
4. **📈 Analytics**: Reference data accumulates for long-term insights
5. **🛡️ Privacy**: Search history doesn't persist indefinitely

The system maintains a **perfect balance** between data freshness, cost efficiency, and performance by using smart 24-hour rolling cleanup rather than crude daily resets!
