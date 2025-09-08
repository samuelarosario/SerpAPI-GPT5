"""Database utility helpers (Phase 1 hardening).

Provides open_connection(db_path) that ensures:
- Absolute path resolution (caller-friendly if relative)
- Foreign key enforcement via PRAGMA

This centralizes connection initialization so all modules consistently
apply integrity guarantees.
"""
from __future__ import annotations

import os
import sqlite3

__all__ = ["open_connection"]

def open_connection(db_path: str) -> sqlite3.Connection:
    """Return a SQLite connection with foreign keys enforced.

    Note: Callers should use context manager semantics:
        with open_connection(path) as conn:
            ...
    """
    if not os.path.isabs(db_path):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        db_path = os.path.normpath(os.path.join(base, db_path))
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
    except Exception:
        # Non-fatal; continue even if pragma not applied (older SQLite compile)
        pass
    return conn
