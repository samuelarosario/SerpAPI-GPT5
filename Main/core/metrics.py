"""Lightweight in-memory metrics counters (P1 observability).

Not persistent; intended for short-lived process diagnostics and test assertions.
"""
from __future__ import annotations

import sys as _sys
import threading
from time import perf_counter

_lock = threading.Lock()

class _Metrics:
    def __init__(self):
        self._counters: dict[str,int] = {
            'api_calls': 0,
            'api_failures': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'retry_attempts': 0,
            'structured_storage_failures': 0,
        }
    def inc(self, name: str, value: int = 1):
        with _lock:
            self._counters[name] = self._counters.get(name,0) + value
    def snapshot(self) -> dict[str,int]:
        with _lock:
            return dict(self._counters)
    def reset(self):  # test helper
        with _lock:
            for k in self._counters.keys():
                self._counters[k] = 0

METRICS = _Metrics()

def timed():  # decorator for optional future use
    def _wrap(fn):
        def inner(*a, **kw):
            start = perf_counter()
            try:
                return fn(*a, **kw)
            finally:
                duration_ms = (perf_counter() - start) * 1000
                METRICS.inc('function_calls')
                METRICS.inc('function_time_ms_total', int(duration_ms))
        return inner
    return _wrap

__all__ = ['METRICS']

# ---- Import Path Guard & Alias Coalescing ----------------------------------
_current = _sys.modules.get(__name__)
for _alias in ('core.metrics', 'Main.core.metrics'):
    _existing = _sys.modules.get(_alias)
    if _existing and _existing is not _current:
        raise RuntimeError(f"Duplicate metrics module load detected (alias={_alias})")
    _sys.modules[_alias] = _current
