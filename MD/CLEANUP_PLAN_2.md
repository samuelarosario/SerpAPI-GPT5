# File Cleanup Plan - Round 2 📂

## Current File Count: ~110+ Python files

Based on our previous optimization (kept 12 essential files), let's clean up the newly accumulated files:

## 🗑️ **FILES TO REMOVE**

### **Root Directory Cleanup:**
```
❌ analyze_py_files.py                 # Analysis utility - no longer needed
❌ cleanup_database.py                 # Redundant - functionality in enhanced_flight_search.py
❌ debug_cache.py                      # Debug utility - temporary
❌ file_recommendations.py             # Analysis utility - no longer needed  
❌ generate_current_schema.py          # One-time utility - completed
❌ test_db_connection.py               # Basic test - functionality covered
❌ search_pom_mnl_sep26.py            # Specific test - can be removed
❌ search_pom_mnl_sep27.py            # Specific test - can be removed
```

### **Main/ Directory Cleanup:**
```
❌ analyze_database.py                 # Analysis utility
❌ api_debug_test.py                   # Debug utility - temporary
❌ apply_schema.py                     # One-time utility - completed
❌ approved_flight_search.py           # Old approval system
❌ check_database.py                   # Analysis utility
❌ demo_approval_prompt.py             # Demo/test file
❌ direct_client_test.py               # Test utility
❌ enhanced_search_demo.py             # Demo file - generated mock data
❌ fixed_flight_test.py                # Test utility
❌ flight_analyzer.py                  # Analysis utility
❌ flight_system_demo.py               # Demo file
❌ pom_mnl_roundtrip_test.py          # Specific test
❌ search_pom_mnl.py                   # Redundant - replaced by enhanced_flight_search.py
❌ simple_api_approval.py              # Old approval system
❌ simple_cache_test.py                # Test utility
❌ simulation_demo.py                  # Demo file
❌ test_approval_system.py             # Test utility
❌ test_db_storage.py                  # Test utility
❌ test_roundtrip_default.py           # Test utility
❌ test_simple_approval.py             # Test utility
```

### **Temp/ Directory - REMOVE ENTIRE FOLDER:**
```
❌ ENTIRE Temp/ FOLDER                # All temporary/debug files
   - 26 files including database cleanup utilities
   - Debug scripts and test files
   - API debugging tools
   - Schema validation reports
```

## ✅ **FILES TO KEEP (Essential System)**

### **Core System Files:**
```
✅ Main/config.py                      # System configuration
✅ Main/enhanced_flight_search.py      # Main flight search engine
✅ Main/flight_processor.py            # Data processing
✅ Main/serpapi_client.py              # API client
✅ Main/api_approval_system.py         # API approval workflow
```

### **Database Files:**
```
✅ DB/schema_upgrade.py                # Database schema management
```

### **Documentation:**
```
✅ README.md                          # Project documentation
✅ requirements.txt                    # Dependencies
✅ All .md documentation files        # System documentation
```

### **Configuration:**
```
✅ .gitignore                         # Git configuration
✅ .venv/                             # Virtual environment
✅ DB/                                # Database directory
```

## 📊 **Cleanup Summary**

**Before Cleanup:** ~110+ files
**After Cleanup:** ~15-20 essential files
**Reduction:** ~85-90% file reduction

## 🎯 **Final Essential System**

After cleanup, you'll have a clean, production-ready system with:
1. **Core search engine** - enhanced_flight_search.py
2. **API client** - serpapi_client.py  
3. **Data processor** - flight_processor.py
4. **Configuration** - config.py
5. **Database schema** - schema_upgrade.py
6. **API approval** - api_approval_system.py
7. **Documentation** - All .md files
8. **Dependencies** - requirements.txt

Ready to execute cleanup? 🚀
