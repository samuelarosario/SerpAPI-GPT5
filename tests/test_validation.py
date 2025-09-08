import unittest
from datetime import date, timedelta
import sys, os, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
MAIN_DIR = ROOT / 'Main'
if str(MAIN_DIR) not in sys.path:
    sys.path.append(str(MAIN_DIR))
from core.common_validation import FlightSearchValidator, parse_price  # type: ignore

class TestValidation(unittest.TestCase):
    def test_validate_date_format(self):
        self.assertTrue(FlightSearchValidator.validate_date('2030-12-30', enforce_horizon=False))
        self.assertFalse(FlightSearchValidator.validate_date('2030/12/30', enforce_horizon=False))
    def test_horizon_positive(self):
        future = (date.today() + timedelta(days=5)).strftime('%Y-%m-%d')
        self.assertTrue(FlightSearchValidator.validate_date(future, enforce_horizon=True))
    def test_horizon_negative(self):
        past = (date.today() + timedelta(days=-1)).strftime('%Y-%m-%d')
        self.assertFalse(FlightSearchValidator.validate_date(past, enforce_horizon=True))

    def test_parse_price(self):
        self.assertEqual(parse_price('599 USD'), (599, 'USD'))
        self.assertEqual(parse_price('1200'), (1200, None))
        self.assertEqual(parse_price(None), (None, None))
        amt, cur = parse_price('bad format')
        self.assertIsNone(amt)

if __name__ == '__main__':
    unittest.main()
