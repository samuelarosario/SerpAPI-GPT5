"""Shared date parsing & horizon utilities.

Standard accepted input formats:
  MM-DD-YYYY
  MM-DD            (assumes current year; if date already passed this year, rolls to next year)

Output format: YYYY-MM-DD

Provides:
  parse_date(str) -> str
  within_horizon(date_str, min_days=1, max_days=365) -> bool
  validate_and_order(outbound, return_date) -> (outbound, return) with error if invalid
"""
from __future__ import annotations

import re
from datetime import date as _date
from datetime import datetime

_MM_DD_YYYY = re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{4})$")
_MM_DD = re.compile(r"^(\d{1,2})-(\d{1,2})$")

class DateParseError(ValueError):
    pass

def parse_date(raw: str) -> str:
    raw = raw.strip()
    today = _date.today()
    m_full = _MM_DD_YYYY.match(raw)
    if m_full:
        mm, dd, yyyy = map(int, m_full.groups())
        try:
            d = _date(yyyy, mm, dd)
        except ValueError:
            raise DateParseError(f"Invalid date components: {raw}")
        return d.strftime('%Y-%m-%d')
    m_short = _MM_DD.match(raw)
    if m_short:
        mm, dd = map(int, m_short.groups())
        # initial attempt current year; if invalid leap day, search next 4 years for valid Feb 29
        candidate_year = today.year
        while True:
            try:
                d = _date(candidate_year, mm, dd)
                break
            except ValueError:
                # Only special-case leap day
                if mm == 2 and dd == 29 and candidate_year - today.year < 6:  # search up to 5 years ahead
                    candidate_year += 1
                    continue
                raise DateParseError(f"Invalid date components: {raw}")
        if d < today:
            # roll forward (respect leap search again)
            candidate_year = d.year + 1
            while True:
                try:
                    d2 = _date(candidate_year, mm, dd)
                    d = d2
                    break
                except ValueError:
                    if mm == 2 and dd == 29 and candidate_year - today.year < 6:
                        candidate_year += 1
                        continue
                    raise DateParseError(f"Invalid rollover date: {raw}")
        return d.strftime('%Y-%m-%d')
    raise DateParseError(f"Unsupported date format: {raw}. Use MM-DD-YYYY or MM-DD")

def within_horizon(date_str: str, min_days: int = 1, max_days: int = 365) -> bool:
    try:
        target = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return False
    today = _date.today()
    delta = (target - today).days
    return min_days <= delta <= max_days

def validate_and_order(outbound: str, return_date: str) -> tuple[str, str]:
    if return_date < outbound:
        raise DateParseError("Return date earlier than outbound date")
    return outbound, return_date

__all__ = [
    'parse_date', 'within_horizon', 'validate_and_order', 'DateParseError'
]
