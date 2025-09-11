"""Week range aggregation service.

Role:
    Orchestrates 7 consecutive day searches (start_date .. start_date+6) and
    produces a consolidated structure with per-day results, flattened flight
    collection, simple price trend metrics, and a summary block.

Inputs:
    client: object providing search_flights(...)
    departure_id / arrival_id: IATA codes
    start_date: str (YYYY-MM-DD) defining day0 of the week window
    **kwargs: forwarded to client.search_flights (passenger counts, filters)

Outputs:
    dict with keys:
        success: bool
        date_range: 'YYYY-MM-DD to YYYY-MM-DD'
        daily_results: { date: { result, day_name, day_offset, ... } }
        best_week_flights: top 10 cheapest flights (heuristic price parse)
        all_week_flights: full flattened list (each augmented with search_date,...)
        price_trend: {'daily_min_prices','daily_avg_prices','weekday_analysis','trend_analysis'}
        summary: derived aggregate metrics and cheapest/most_expensive day info

Side Effects:
    - Emits structured log events efs.week.* for observability.
    - Calls client's search_flights which may access cache / API.

Failure Handling:
    - Individual day failures are recorded with an 'error' key; others proceed.
    - Entire operation returns success=False only if 0/7 days succeed.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any
import logging

from Main.core.structured_logging import log_event  # type: ignore
from Main.constants import Event, emit

class WeekRangeAggregator:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger(__name__)

    def run_week(self, client, departure_id: str, arrival_id: str, start_date: str, **kwargs) -> dict[str, Any]:  # noqa: ANN401
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            return {
                'success': False,
                'error': f'Invalid start_date format: {start_date}. Use YYYY-MM-DD',
                'source': 'week_range_validation'
            }
        end_dt = start_dt + timedelta(days=6)
        end_date = end_dt.strftime('%Y-%m-%d')
        self.logger.info("Week search start %s->%s %s to %s", departure_id, arrival_id, start_date, end_date)
        emit(Event.WEEK_START, log_event, route=f"{departure_id}-{arrival_id}", start_date=start_date)

        daily_results: dict[str, Any] = {}
        all_flights: list[dict[str, Any]] = []
        successful_searches = 0
        total_flights_found = 0

        for day_offset in range(7):
            search_date = (start_dt + timedelta(days=day_offset)).strftime('%Y-%m-%d')
            day_name = (start_dt + timedelta(days=day_offset)).strftime('%A')
            emit(Event.WEEK_DAY_START, log_event, date=search_date, day_offset=day_offset)
            daily_result = client.search_flights(departure_id, arrival_id, search_date, **kwargs)
            if daily_result.get('success'):
                successful_searches += 1
                daily_results[search_date] = {
                    'result': daily_result,
                    'day_name': day_name,
                    'day_offset': day_offset
                }
                data = daily_result.get('data', {})
                best_flights = data.get('best_flights', [])
                other_flights = data.get('other_flights', [])
                # Filter out synthetic inbound fallback flights (tagged by inbound_merge)
                other_flights = [f for f in other_flights if not f.get('__inbound_fallback__')]
                for flight in best_flights + other_flights:
                    f2 = flight.copy()
                    f2['search_date'] = search_date
                    f2['day_name'] = day_name
                    f2['day_offset'] = day_offset
                    f2['is_best'] = flight in best_flights
                    all_flights.append(f2)
                daily_count = len(best_flights) + len(other_flights)
                total_flights_found += daily_count
                emit(Event.WEEK_DAY_SUCCESS, log_event, date=search_date, flights=daily_count)
            else:
                daily_results[search_date] = {
                    'result': daily_result,
                    'day_name': day_name,
                    'day_offset': day_offset,
                    'error': daily_result.get('error', 'Search failed')
                }
                emit(Event.WEEK_DAY_ERROR, log_event, date=search_date, error=daily_result.get('error'))

        # Sort by price heuristic
        def _price(f: dict[str, Any]):
            s = f.get('price', '9999 USD')
            try:
                return float(s.replace(' USD', '').replace(',', ''))
            except Exception:  # pragma: no cover - fallback for malformed price
                return 9999.0
        all_flights.sort(key=_price)

        price_trend = self._analyze_price_trend(daily_results)
        summary = self._build_summary(start_date, end_date, price_trend, successful_searches, total_flights_found)
        result = {
            'success': successful_searches > 0,
            'source': 'week_range',
            'date_range': f"{start_date} to {end_date}",
            'daily_results': daily_results,
            'best_week_flights': all_flights[:10],
            'all_week_flights': all_flights,
            'price_trend': price_trend,
            'summary': summary
        }
        if successful_searches == 0:
            result['error'] = 'No successful searches in the 7-day range'
        elif successful_searches < 7:
            result['warning'] = f'Only {successful_searches}/7 days returned results'
        emit(Event.WEEK_COMPLETE, log_event, successful_days=successful_searches, total_flights=total_flights_found)
        return result

    def _analyze_price_trend(self, daily_results: dict) -> dict[str, Any]:  # noqa: ANN001
        daily_min_prices = {}
        daily_avg_prices = {}
        weekday_analysis = {'weekday': [], 'weekend': []}
        for date_str, day_data in daily_results.items():
            if 'error' in day_data:
                continue
            day_name = day_data['day_name']
            data = day_data['result'].get('data', {})
            flights = data.get('best_flights', []) + data.get('other_flights', [])
            prices = []
            for f in flights:
                try:
                    p = float(f.get('price', '0').replace(' USD', '').replace(',', ''))
                    if p > 0:
                        prices.append(p)
                except Exception:
                    continue
            if prices:
                daily_min_prices[date_str] = min(prices)
                daily_avg_prices[date_str] = sum(prices) / len(prices)
                if day_name in ['Saturday', 'Sunday']:
                    weekday_analysis['weekend'].append(date_str)
                else:
                    weekday_analysis['weekday'].append(date_str)
        trend = {'overall_price_trend': 'stable'}
        if len(daily_min_prices) > 1:
            sorted_days = sorted(daily_min_prices.keys())
            first_day, last_day = sorted_days[0], sorted_days[-1]
            if daily_min_prices[last_day] < daily_min_prices[first_day]:
                trend['overall_price_trend'] = 'decreasing'
            elif daily_min_prices[last_day] > daily_min_prices[first_day]:
                trend['overall_price_trend'] = 'increasing'
        return {
            'daily_min_prices': daily_min_prices,
            'daily_avg_prices': daily_avg_prices,
            'weekday_analysis': weekday_analysis,
            'trend_analysis': trend
        }

    def _build_summary(self, start_date: str, end_date: str, price_trend: dict[str, Any], success_days: int, total_flights: int) -> dict[str, Any]:
        summary = {
            'total_days_searched': 7,
            'successful_searches': success_days,
            'failed_searches': 7 - success_days,
            'total_flights_found': total_flights,
            'avg_flights_per_day': round(total_flights / max(success_days, 1), 1),
            'date_range': f"{start_date} to {end_date}",
            'cheapest_day': None,
            'most_expensive_day': None
        }
        if price_trend['daily_min_prices']:
            mins = price_trend['daily_min_prices']
            cheapest = min(mins.items(), key=lambda x: x[1])
            expensive = max(mins.items(), key=lambda x: x[1])
            summary['cheapest_day'] = {'date': cheapest[0], 'price': cheapest[1]}
            summary['most_expensive_day'] = {'date': expensive[0], 'price': expensive[1]}
        return summary

__all__ = ['WeekRangeAggregator']
