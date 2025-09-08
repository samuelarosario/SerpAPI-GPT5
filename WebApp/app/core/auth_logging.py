import json, time, os, threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional

_LOG_PATH = Path("WebApp/logs/auth_events.jsonl")
_LOCK = threading.Lock()


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_auth(event: str, email: Optional[str] = None, success: Optional[bool] = None, detail: Optional[str] = None, extra: Optional[dict[str, Any]] = None) -> None:
    record = {
        "ts": _ts(),
        "event": event,
        "email": email,
        "success": success,
        "detail": detail,
    }
    if extra:
        record.update(extra)
    line = json.dumps(record, ensure_ascii=False)
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        with _LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def tail_auth_log(lines: int = 50) -> list[dict[str, Any]]:
    if not _LOG_PATH.exists():
        return []
    with _LOG_PATH.open("r", encoding="utf-8") as fh:
        data = fh.readlines()[-lines:]
    out: list[dict[str, Any]] = []
    for raw in data:
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return out
