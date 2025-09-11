"""Inbound merge strategy.

Role:
    Ensure a round-trip result contains an inbound (return) leg. Some SerpAPI
    responses occasionally omit the return flights even when a return_date is
    requested. This service performs a fallback one-way search for the reverse
    direction (arrival->departure on return_date) and merges those flights into
    the existing payload.

Inputs:
    api_data: dict | None - raw aggregated API data structure (mutated in place)
    search_params: dict - includes 'departure_id','arrival_id','return_date', passenger counts, etc.
    api_client: object - must implement search_one_way(...)

Outputs:
    Returns the (possibly modified) api_data dict. If no action required or an
    error occurs, the original structure is returned unchanged.

Side Effects:
    - Makes an external API call if inbound leg is missing.
    - Emits structured log events (efs.inbound.*).
    - Mutates api_data['other_flights'] by appending inbound flights.

Failure Handling:
    Completely fails open: any exception is logged and the original api_data is
    returned so the caller never hard-fails due to merge enrichment.
"""
from __future__ import annotations
from typing import Any
import logging

from Main.core.structured_logging import log_event, log_exception  # type: ignore
from Main.constants import Event, emit

class InboundMergeStrategy:
    """Encapsulates logic to detect missing inbound segments and perform a fallback one-way search.

    Contract:
        ensure_inbound(api_data, params, api_client) -> dict (possibly mutated api_data)
    """
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger(__name__)

    def ensure_inbound(self, api_data: dict[str, Any] | None, search_params: dict[str, Any], api_client) -> dict[str, Any] | None:  # noqa: ANN401
        if not api_data:
            return api_data
        ret = search_params.get('return_date')
        if not ret:
            return api_data
        dep = str(search_params.get('departure_id', '')).upper()
        arr = str(search_params.get('arrival_id', '')).upper()

        def _has_inbound(d: dict[str, Any], dep_code: str, arr_code: str, ret_date: str) -> bool:
            flights = (d.get('best_flights') or []) + (d.get('other_flights') or [])
            for f in flights:
                for s in (f.get('flights') or []):
                    da = (s.get('departure_airport') or {})
                    aa = (s.get('arrival_airport') or {})
                    did = str(da.get('id') or '').upper()
                    aid = str(aa.get('id') or '').upper()
                    dt = str(da.get('time') or '')
                    at = str(aa.get('time') or '')
                    if (did == arr_code and aid == dep_code) or (dt.startswith(ret_date) or at.startswith(ret_date)):
                        return True
            return False

        try:
            if _has_inbound(api_data, dep, arr, ret):
                return api_data
            self.logger.info("Inbound missing; fetching fallback one-way %s->%s on %s", arr, dep, ret)
            emit(Event.INBOUND_MISSING, log_event, route=f"{dep}-{arr}", return_date=ret)
            inbound = api_client.search_one_way(departure_id=arr, arrival_id=dep, outbound_date=ret,
                                                adults=search_params.get('adults', 1),
                                                children=search_params.get('children', 0),
                                                infants_in_seat=search_params.get('infants_in_seat', 0),
                                                infants_on_lap=search_params.get('infants_on_lap', 0),
                                                travel_class=search_params.get('travel_class', 1),
                                                currency=search_params.get('currency', 'USD'))
            if inbound and inbound.get('success') and isinstance(api_data, dict):
                in_data = inbound.get('data') or {}
                api_data.setdefault('other_flights', [])
                tagged = []
                for _f in (in_data.get('best_flights') or []) + (in_data.get('other_flights') or []):
                    f2 = dict(_f)
                    f2['__inbound_fallback__'] = True
                    tagged.append(f2)
                api_data['other_flights'].extend(tagged)
                added = len((in_data.get('best_flights') or [])) + len((in_data.get('other_flights') or []))
                self.logger.info("Merged inbound fallback flights: +%d", added)
                emit(Event.INBOUND_MERGED, log_event, added=added)
            return api_data
        except Exception as e:  # pragma: no cover (defensive)
            self.logger.warning("Inbound fallback failed: %s", e)
            log_exception(str(Event.INBOUND_ERROR), exc=e)
            return api_data

__all__ = ['InboundMergeStrategy']
