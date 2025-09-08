"""Common validation and rate limiting utilities."""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, List, Optional
import re
import os, sys, pathlib

# Ensure Main directory on path for `config` import when module loaded in isolation during tests
MAIN_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(MAIN_DIR) not in sys.path:
    sys.path.append(str(MAIN_DIR))

from Main.config import RATE_LIMIT_CONFIG, VALIDATION_RULES
from date_utils import within_horizon as _within_horizon

class RateLimiter:
    def __init__(self):
        self._minute: List[datetime] = []
        self._hour: List[datetime] = []
    def can_make_request(self) -> bool:
        now = datetime.now()
        self._minute = [t for t in self._minute if now - t < timedelta(minutes=1)]
        self._hour = [t for t in self._hour if now - t < timedelta(hours=1)]
        return (len(self._minute) < RATE_LIMIT_CONFIG['requests_per_minute'] and
                len(self._hour) < RATE_LIMIT_CONFIG['requests_per_hour'])
    def record_request(self) -> None:
        now = datetime.now(); self._minute.append(now); self._hour.append(now)
    def reset(self) -> None:
        self._minute.clear(); self._hour.clear()

class FlightSearchValidator:
    @staticmethod
    def validate_airport_code(code: str) -> bool:
        return bool(code) and len(code) == VALIDATION_RULES['airport_code_length'] and code.isalpha() and code.isupper()
    @staticmethod
    def validate_date(date_str: str, enforce_horizon: bool = True) -> bool:
        from datetime import datetime as _dt
        try: _dt.strptime(date_str, '%Y-%m-%d')
        except ValueError: return False
        if not enforce_horizon: return True
        return _within_horizon(
            date_str,
            min_days=VALIDATION_RULES['min_search_days_ahead'],
            max_days=VALIDATION_RULES['max_search_days_ahead']
        )
    @staticmethod
    def validate_passengers(adults: int, children: int, infants_seat: int, infants_lap: int, enforce_infant_rule: bool = True) -> bool:
        total = adults + children + infants_seat + infants_lap
        if adults < 1 or total > VALIDATION_RULES['max_passengers'] or any(x < 0 for x in [adults, children, infants_seat, infants_lap]):
            return False
        if enforce_infant_rule and infants_lap > adults: return False
        return True
    @staticmethod
    def validate_search_params(params: Dict[str, Any], *, enforce_horizon: bool = True, enforce_infant_rule: bool = True) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        for field in VALIDATION_RULES['required_fields']:
            if not params.get(field): errors.append(f"Required field missing: {field}")
        if 'departure_id' in params and not FlightSearchValidator.validate_airport_code(params.get('departure_id','')):
            errors.append(f"Invalid departure airport code: {params.get('departure_id')}")
        if 'arrival_id' in params and not FlightSearchValidator.validate_airport_code(params.get('arrival_id','')):
            errors.append(f"Invalid arrival airport code: {params.get('arrival_id')}")
        if params.get('outbound_date') and not FlightSearchValidator.validate_date(params['outbound_date'], enforce_horizon):
            errors.append(f"Invalid outbound date: {params['outbound_date']}")
        if params.get('return_date') and not FlightSearchValidator.validate_date(params['return_date'], enforce_horizon):
            errors.append(f"Invalid return date: {params['return_date']}")
        if not FlightSearchValidator.validate_passengers(
            params.get('adults',1), params.get('children',0), params.get('infants_in_seat',0), params.get('infants_on_lap',0), enforce_infant_rule
        ): errors.append('Invalid passenger configuration')
        if params.get('outbound_date') and params.get('return_date'):
            from datetime import datetime as _dt
            try:
                if _dt.strptime(params['return_date'],'%Y-%m-%d') < _dt.strptime(params['outbound_date'],'%Y-%m-%d'):
                    errors.append('Return date earlier than outbound date')
            except ValueError: pass
        return (len(errors)==0, errors)

_price_regex = re.compile(r"^(?P<amount>\d+(?:[.,]\d+)?)\s*(?P<currency>[A-Z]{3})?$")

def parse_price(raw: Any) -> Tuple[Optional[int], Optional[str]]:
    if raw is None: return None, None
    if isinstance(raw,(int,float)): return int(raw), None
    s = str(raw).strip(); m = _price_regex.match(s)
    if not m: return None, None
    amt = m.group('amount').replace(',','')
    try: amt_int = int(float(amt))
    except ValueError: return None, m.group('currency')
    return amt_int, m.group('currency')

__all__ = ['RateLimiter','FlightSearchValidator','parse_price']
