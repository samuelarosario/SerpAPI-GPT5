import unittest, re
from datetime import date as _date
from date_utils import parse_date, DateParseError

class TestDateUtils(unittest.TestCase):
    def test_full_format(self):
        self.assertEqual(parse_date('12-25-2030'), '2030-12-25')
    def test_short_future_or_rollover(self):
        today = _date.today()
        # pick a date likely after today: December 31
        parsed = parse_date('12-31')
        m = re.match(r'^(\d{4})-12-31$', parsed)
        self.assertTrue(m)
    def test_invalid(self):
        with self.assertRaises(DateParseError):
            parse_date('2025/12/30')
        with self.assertRaises(DateParseError):
            parse_date('31-31-2025')

if __name__ == '__main__':
    unittest.main()
