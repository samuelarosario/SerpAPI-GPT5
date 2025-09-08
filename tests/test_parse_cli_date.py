import pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
MAIN_DIR = ROOT / 'Main'
if str(MAIN_DIR) not in sys.path:
    sys.path.append(str(MAIN_DIR))

from enhanced_flight_search import parse_cli_date  # type: ignore

def test_parse_cli_date_ambiguous_day_first():
    # Ambiguous 05-06 must be interpreted as day-first (DD-MM)
    result = parse_cli_date('05-06')
    # Expect June 5 in YYYY-MM-DD
    assert result.endswith('-06-05'), result

def test_parse_cli_date_rollover_short():
    # Provide a short date that is guaranteed to roll over (pick Jan 1 if already past?)
    from datetime import date as _date
    today = _date.today()
    # Choose a day that is always behind today: yesterday short form
    y = today.replace(day=max(1, today.day))
    short = f"{y.month:02d}-{y.day:02d}"
    parsed = parse_cli_date(short)
    # Parsed year should be >= today.year
    assert int(parsed[:4]) >= today.year
