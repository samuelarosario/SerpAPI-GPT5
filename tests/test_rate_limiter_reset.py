import pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[1]
MAIN_DIR = ROOT / 'Main'
if str(MAIN_DIR) not in sys.path:
    sys.path.append(str(MAIN_DIR))

from core.common_validation import RateLimiter  # type: ignore

def test_rate_limiter_reset():
    rl = RateLimiter()
    # simulate filling minute window
    for _ in range(5):
        rl.record_request()
    assert len(rl._minute) == 5
    rl.reset()
    assert len(rl._minute) == 0 and len(rl._hour) == 0
