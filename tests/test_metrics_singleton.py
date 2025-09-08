import importlib
import sys
from Main.core.metrics import METRICS as METRICS_A  # type: ignore


def test_metrics_singleton_alias_identity():
    alt = importlib.import_module('Main.core.metrics')  # should not re-execute
    assert alt.METRICS is METRICS_A
    assert sys.modules['core.metrics'] is sys.modules['Main.core.metrics']
    # Increment via one alias and verify via the other
    METRICS_A.inc('api_calls')
    snap = alt.METRICS.snapshot()
    assert snap['api_calls'] == 1