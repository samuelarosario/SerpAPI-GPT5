from Main.services.week_aggregator import WeekRangeAggregator

class DummyClient:
    def __init__(self, success_dates):
        self.success_dates = set(success_dates)
        self.calls = []
    def search_flights(self, dep, arr, date, **kwargs):
        self.calls.append(date)
        if date in self.success_dates:
            return {'success': True, 'data': {'best_flights': [{'price': '100 USD', 'flights': []}], 'other_flights': []}}
        return {'success': False, 'error': 'fail'}

def test_week_aggregator_basic():
    agg = WeekRangeAggregator()
    client = DummyClient(success_dates=['2025-12-01', '2025-12-03'])
    res = agg.run_week(client, 'AAA', 'BBB', '2025-12-01')
    assert res['success'] is True  # at least one day succeeded
    assert res['summary']['successful_searches'] == 2
    assert 'price_trend' in res
    assert 'daily_results' in res and len(res['daily_results']) == 7
