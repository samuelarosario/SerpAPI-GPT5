"""Service registry for flight search related helper services.

Each service should expose a lightweight, side-effect free function or a small class.
Dynamic lookups allow future AI or plugin mechanisms to discover capabilities.
"""
from __future__ import annotations
from typing import Any, Callable, Dict

from . import inbound_merge, week_aggregator, cli_date_parser

# Instantiate strategy/service classes once for lightweight stateless usage
_INBOUND_STRATEGY = inbound_merge.InboundMergeStrategy()
_WEEK_AGG = week_aggregator.WeekRangeAggregator()

REGISTRY: Dict[str, Any] = {
    'inbound.ensure': _INBOUND_STRATEGY.ensure_inbound,
    'week.run': _WEEK_AGG.run_week,
    'cli.parse_date': cli_date_parser.parse_cli_date,
}

__all__ = ['REGISTRY']
