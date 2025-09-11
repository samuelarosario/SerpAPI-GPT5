"""CLI date parsing (extracted) with backward-compatible logic.

Re-exported from enhanced_flight_search for legacy imports.
"""
from __future__ import annotations
from date_utils import parse_date as _legacy_parse  # type: ignore

# Direct copy of logic (with minor formatting) from enhanced_flight_search.parse_cli_date

def parse_cli_date(raw: str) -> str:
    raw = raw.strip()
    parts = raw.split('-')
    if len(parts) not in (2, 3):
        return _legacy_parse(raw)
    try:
        a = int(parts[0]); b = int(parts[1]); year = int(parts[2]) if len(parts) == 3 else None
    except ValueError:
        return _legacy_parse(raw)
    if a > 12:
        use_day_first = True
    elif b > 12:
        use_day_first = False
    else:
        use_day_first = True
    day, month = (a, b) if use_day_first else (b, a)
    from datetime import date as _date
    today = _date.today()
    if year is None:
        year = today.year
    try:
        candidate = _date(year, month, day)
    except ValueError:
        return _legacy_parse(raw)
    if candidate < today and len(parts) < 3:
        # Roll forward one year if no explicit year provided
        try:
            candidate = _date(year + 1, month, day)
        except ValueError:
            return _legacy_parse(raw)
    return candidate.strftime('%Y-%m-%d')

__all__ = ['parse_cli_date']
