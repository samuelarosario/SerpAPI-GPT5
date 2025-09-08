import os, sys
from datetime import date as _date

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MAIN_DIR = os.path.join(ROOT, 'Main')
if MAIN_DIR not in sys.path:
    sys.path.insert(0, MAIN_DIR)

from enhanced_flight_search import parse_cli_date  # type: ignore


def test_ambiguous_day_first():
    # 05-06 ambiguous -> treated as DD-MM => 5 June current year or next year rollover logic handled internally
    parsed = parse_cli_date('05-06')
    assert parsed.endswith('-06-05'), f"Expected DD-MM interpretation, got {parsed}"


def test_first_component_gt12_forces_day_first():
    parsed = parse_cli_date('25-07')
    # Day 25 month 07
    assert parsed.endswith('-07-25'), f"Unexpected parsing for 25-07: {parsed}"


def test_second_component_gt12_forces_month_first():
    # 07-25 -> month=07 day=25 since second>12 means first is month
    parsed = parse_cli_date('07-25')
    assert parsed.endswith('-07-25'), f"Month-first legacy path failed: {parsed}"


def test_year_preserved():
    parsed = parse_cli_date('05-06-2031')
    assert parsed == '2031-06-05'
