"""Central enumerations and helpers for structured events & metrics.

Using enums avoids drift in event name strings and enables refactors / search.
emit() provides a tolerant thin wrapper so callers can supply either enum or
string while we converge on full adoption.
"""
from enum import StrEnum
from typing import Union, Any

class Event(StrEnum):
    # High-level generic events
    SEARCH_START = 'efs.search.start'
    SEARCH_SUCCESS = 'efs.search.success'
    SEARCH_ERROR = 'efs.search.error'
    CACHE_HIT = 'efs.cache.hit'
    CACHE_MISS = 'efs.cache.miss'
    API_REQUEST = 'efs.api.request'
    API_ERROR = 'efs.api.error'
    STORE_RAW_SUCCESS = 'efs.store.raw.success'
    STORE_RAW_ERROR = 'efs.store.raw.error'
    STORE_STRUCTURED_SUCCESS = 'efs.store.structured.success'
    STORE_STRUCTURED_ERROR = 'efs.store.structured.error'
    INBOUND_MISSING = 'efs.inbound.missing'
    INBOUND_MERGED = 'efs.inbound.merged'
    INBOUND_ERROR = 'efs.inbound.error'
    WEEK_START = 'efs.week.start'
    WEEK_DAY_START = 'efs.week.day.start'
    WEEK_DAY_SUCCESS = 'efs.week.day.success'
    WEEK_DAY_ERROR = 'efs.week.day.error'
    WEEK_COMPLETE = 'efs.week.complete'

class Metric(StrEnum):
    SEARCH_DURATION_MS = 'search.duration_ms'
    FLIGHTS_FOUND = 'search.flights_found'
    WEEK_LOW_PRICE = 'search.week.low_price'
    WEEK_HIGH_PRICE = 'search.week.high_price'
    STRUCTURED_STORAGE_FAILURES = 'structured_storage_failures'

def emit(event: Union[Event, str], logger_func, **fields: Any) -> None:
    """Helper to standardize structured log_event usage.

    Accepts either an Event enum value or a raw string for backward compatibility.
    """
    try:
        logger_func(str(event), **fields)
    except Exception:
        # Fail open; logging must never raise to caller
        pass

__all__ = ['Event','Metric','emit']
