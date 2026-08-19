import unittest
from datetime import date

from data.ingestion.xsmb_source_b import extract_date_block, parse_full27_block


FIXTURE = """XSMB Thứ 4, 12/08/2026
---
ĐB  | 82326
G1  | 31773
G2  | 64497  | 88592
G3  | 50195  | 46812  | 80982
66597  | 76120  | 13434
G4  | 0172  | 0162  | 3526  | 0188
G5  | 3050  | 2194  | 4509
7308  | 9434  | 6888
G6  | 540  | 059  | 081
G7  | 21  | 97  | 42  | 00

XSMB Thứ 3, 11/08/2026
---
ĐB  | 11111
"""


class XsmbSourceBTests(unittest.TestCase):
    def test_extracts_only_target_date_block(self):
        block = extract_date_block(FIXTURE, date(2026, 8, 12))
        self.assertIn("82326", block)
        self.assertNotIn("11111", block)

    def test_full27_counts_and_order(self):
        block = extract_date_block(FIXTURE, date(2026, 8, 12))
        full = parse_full27_block(block)
        self.assertEqual(len(full), 27)
        self.assertEqual(full[0], "82326")
        self.assertEqual(full[-1], "00")

    def test_missing_date_denies(self):
        with self.assertRaises(ValueError):
            extract_date_block(FIXTURE, date(2026, 8, 13))


if __name__ == "__main__":
    unittest.main()
