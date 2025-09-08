"""Lightweight structured JSON logging (append-only JSONL).

Environment variable FLIGHT_JSON_LOG can override default path.
Non-fatal on I/O errors.
"""
from __future__ import annotations

import datetime
import json
import os
import socket
import threading
import traceback
from typing import Callable
from typing import Any, Optional

_lock = threading.Lock()

DEFAULT_JSON_LOG = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs', 'flight_events.jsonl'))
LOG_PATH = os.environ.get('FLIGHT_JSON_LOG', DEFAULT_JSON_LOG)

_ROTATE_MAX_BYTES = int(os.environ.get('FLIGHT_JSON_LOG_MAX', '5242880'))  # 5MB default
_ROTATE_KEEP = int(os.environ.get('FLIGHT_JSON_LOG_KEEP', '3'))

def _rotate_if_needed(path: str):
    if _ROTATE_MAX_BYTES <= 0:
        return
    try:
        if os.path.isfile(path) and os.path.getsize(path) > _ROTATE_MAX_BYTES:
            ts = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            rotated = f"{path}.{ts}"
            try:
                os.replace(path, rotated)
            except Exception:
                return
            # Prune old rotated files beyond keep count
            base = os.path.basename(path)
            prefix = base + '.'
            parent = os.path.dirname(path)
            rotated_files = sorted([f for f in os.listdir(parent) if f.startswith(prefix)], reverse=True)
            for f in rotated_files[_ROTATE_KEEP:]:
                try:
                    os.remove(os.path.join(parent, f))
                except Exception:
                    pass
    except Exception:
        pass

def _ensure_dir(path: str):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except Exception:
        pass

def log_event(event: str, *, search_id: Optional[str] = None, level: str = 'INFO', **fields: Any) -> None:
    record: dict[str, Any] = {
        'ts': datetime.datetime.now(datetime.UTC).isoformat(),
        'event': event,
        'level': level,
        'search_id': search_id,
        'host': socket.gethostname(),
    }
    # Merge extra fields (flat)
    for k, v in fields.items():
        # Avoid overwriting core keys unintentionally
        if k not in record:
            record[k] = v
    line = json.dumps(record, ensure_ascii=False)
    try:
        _ensure_dir(LOG_PATH)
        with _lock:
            _rotate_if_needed(LOG_PATH)
            with open(LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
    except Exception:
        # Silent fail – structured logging must not break primary flow
        pass

def log_exception(event: str, *, search_id: Optional[str] = None, exc: BaseException | None = None, **fields: Any) -> None:
    exc_info = None
    if exc is not None:
        exc_info = {
            'type': type(exc).__name__,
            'message': str(exc),
            'traceback': traceback.format_exc(limit=5)
        }
    log_event(event, search_id=search_id, level='ERROR', exception=exc_info, **fields)

__all__ = ['log_event','log_exception','LOG_PATH']