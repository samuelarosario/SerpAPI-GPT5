"""Side-effect boundary abstractions.

Role:
    Provide small Protocol-driven wrappers for external interactions so higher
    level services can depend on interfaces instead of concrete libraries.

Contracts:
    HttpClient.get/post
    Clock.now
    EnvProvider.get

Migration Path:
    Future async version can implement parallel async protocols and swap
    injection at composition root without rewriting business logic.
"""
from __future__ import annotations
from typing import Protocol, Any, Mapping
import requests
import os
import time

class HttpClient(Protocol):
    def get(self, url: str, params: Mapping[str, Any] | None = None, timeout: float | None = None) -> Any: ...
    def post(self, url: str, data: Any | None = None, json: Any | None = None, timeout: float | None = None) -> Any: ...

class RequestsHttpClient:
    """Thin wrapper over requests.Session fulfilling HttpClient protocol."""
    def __init__(self, session: requests.Session | None = None):
        self._s = session or requests.Session()
    def get(self, url: str, params: Mapping[str, Any] | None = None, timeout: float | None = None):
        return self._s.get(url, params=params, timeout=timeout)
    def post(self, url: str, data: Any | None = None, json: Any | None = None, timeout: float | None = None):
        return self._s.post(url, data=data, json=json, timeout=timeout)

class Clock(Protocol):
    def now(self) -> float: ...

class SystemClock:
    def now(self) -> float:
        return time.time()

class EnvProvider(Protocol):
    def get(self, key: str, default: str | None = None) -> str | None: ...

class OsEnvProvider:
    def get(self, key: str, default: str | None = None) -> str | None:
        return os.environ.get(key, default)

__all__ = ['HttpClient','RequestsHttpClient','Clock','SystemClock','EnvProvider','OsEnvProvider']
