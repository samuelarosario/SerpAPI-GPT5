import os, sys, shutil, pathlib
import pytest

# Ensure project root and Main directory are on sys.path so both 'Main.*' and legacy 'core.*' style imports resolve.
ROOT = pathlib.Path(__file__).resolve().parents[1]
MAIN = ROOT / 'Main'
for p in (ROOT, MAIN):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# Lightweight fixtures -------------------------------------------------------

@pytest.fixture()
def metrics_reset():
    from Main.core.metrics import METRICS  # type: ignore
    METRICS.reset()
    yield
    METRICS.reset()

@pytest.fixture()
def db_copy(tmp_path):
    """Provide a temp copy of the main DB file if it exists, else skip."""
    src = ROOT / 'DB' / 'Main_DB.db'
    if not src.exists():
        pytest.skip('Main_DB.db missing; skipping DB dependent test')
    dst = tmp_path / 'test.db'
    shutil.copyfile(src, dst)
    return dst
