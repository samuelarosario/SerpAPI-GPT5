import types
from Main.services.inbound_merge import InboundMergeStrategy

class DummyApiClient:
    def __init__(self, response):
        self._response = response
        self.calls = []
    def search_one_way(self, **kwargs):  # capture params
        self.calls.append(kwargs)
        return self._response

def test_inbound_merge_no_action_when_inbound_present():
    strat = InboundMergeStrategy()
    api_data = {
        'best_flights': [
            {
                'flights': [
                    {
                        'departure_airport': {'id': 'AAA', 'time': '2025-12-01T10:00'},
                        'arrival_airport': {'id': 'BBB', 'time': '2025-12-01T12:00'}
                    },
                    {
                        'departure_airport': {'id': 'BBB', 'time': '2025-12-08T10:00'},
                        'arrival_airport': {'id': 'AAA', 'time': '2025-12-08T12:00'}
                    }
                ]
            }
        ]
    }
    params = {'departure_id': 'AAA', 'arrival_id': 'BBB', 'return_date': '2025-12-08'}
    dummy = DummyApiClient({'success': True, 'data': {}})
    out = strat.ensure_inbound(api_data, params, dummy)
    assert out is api_data
    assert dummy.calls == []  # no fallback call

def test_inbound_merge_adds_missing_inbound():
    strat = InboundMergeStrategy()
    api_data = {
        'best_flights': [
            {
                'flights': [
                    {
                        'departure_airport': {'id': 'AAA', 'time': '2025-12-01T10:00'},
                        'arrival_airport': {'id': 'BBB', 'time': '2025-12-01T12:00'}
                    }
                ]
            }
        ],
        'other_flights': []
    }
    inbound_payload = {
        'success': True,
        'data': {
            'best_flights': [
                {
                    'flights': [
                        {
                            'departure_airport': {'id': 'BBB', 'time': '2025-12-08T09:00'},
                            'arrival_airport': {'id': 'AAA', 'time': '2025-12-08T11:00'}
                        }
                    ]
                }
            ]
        }
    }
    params = {'departure_id': 'AAA', 'arrival_id': 'BBB', 'return_date': '2025-12-08'}
    dummy = DummyApiClient(inbound_payload)
    out = strat.ensure_inbound(api_data, params, dummy)
    assert len(out.get('other_flights', [])) == 1  # inbound flight merged
    assert dummy.calls and dummy.calls[0]['departure_id'] == 'BBB'
