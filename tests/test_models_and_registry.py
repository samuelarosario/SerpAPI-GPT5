from Main.models.flight_models import FlightSearchParams, FlightResult, Segment, Layover, PriceInsights, NormalizedSearch
from Main.services import REGISTRY

def test_flight_search_params_defaults():
    p = FlightSearchParams(departure_id='MNL', arrival_id='POM', outbound_date='2025-12-01')
    assert p.adults == 1
    assert p.currency == 'USD'


def test_segment_aliases():
    seg = Segment(departure_airport_code='MNL', arrival_airport_code='POM')
    assert seg.departure_airport == 'MNL'
    assert seg.arrival_airport == 'POM'


def test_registry_keys():
    assert 'inbound.ensure' in REGISTRY
    assert callable(REGISTRY['inbound.ensure'])
    assert 'week.run' in REGISTRY


def test_normalized_search_structure():
    params = FlightSearchParams(departure_id='MNL', arrival_id='POM', outbound_date='2025-12-01')
    ns = NormalizedSearch(search_id='abc123', params=params)
    assert ns.search_id == 'abc123'
    assert ns.params.departure_id == 'MNL'
