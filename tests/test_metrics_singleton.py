import os, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
MAIN = ROOT / 'Main'
for p in (str(ROOT), str(MAIN)):
    if p not in sys.path:
        sys.path.insert(0, p)
from core.metrics import METRICS as METRICS_A  # canonical import
import importlib, sys

def test_metrics_singleton_alias_identity():
    alt = importlib.import_module('Main.core.metrics')  # should not re-execute
    assert alt.METRICS is METRICS_A
    assert sys.modules['core.metrics'] is sys.modules['Main.core.metrics']
    # Increment via one alias and verify via the other
    METRICS_A.inc('api_calls')
    snap = alt.METRICS.snapshot()
    assert snap['api_calls'] == 1