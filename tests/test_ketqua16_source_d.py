import unittest
from datetime import date

from data.ingestion.ketqua16_source_d import extract_date_block, parse_full27_block


FIXTURE = """Thứ tư ngày 12-08-2026
Ký tự | 1EM-2EM
Đặc biệt | 82326
Giải nhất | 31773
Giải nhì | 64497 88592
Giải ba | 50195 46812 80982 66597 76120 13434
Giải tư | 0172 0162 3526 0188
Giải năm | 3050 2194 4509 7308 9434 6888
Giải sáu | 540 059 081
Giải bảy | 21 97 42 00

Thứ ba ngày 11-08-2026
Đặc biệt | 11111
"""


class Ketqua16SourceDTests(unittest.TestCase):
    def test_extracts_only_target_date_block(self):
        block = extract_date_block(FIXTURE, date(2026, 8, 12))
        self.assertIn("82326", block)
        self.assertNotIn("11111", block)

    def test_parses_full27(self):
        full = parse_full27_block(extract_date_block(FIXTURE, date(2026, 8, 12)))
        self.assertEqual(len(full), 27)
        self.assertEqual(full[0], "82326")
        self.assertEqual(full[-1], "00")

    def test_missing_date_denies(self):
        with self.assertRaises(ValueError):
            extract_date_block(FIXTURE, date(2026, 8, 13))


if __name__ == "__main__":
    unittest.main()
