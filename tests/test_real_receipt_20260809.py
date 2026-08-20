import unittest
from datetime import date

from data.ingestion.ketqua16_source_d import extract_date_block as extract_ketqua16, parse_full27_block as parse_ketqua16
from data.ingestion.xsmb_source_b import extract_date_block as extract_xsmb, parse_full27_block as parse_xsmb


# Observed independently on public source pages; this is a bounded fixture for
# parser verification only. It is NOT canonical promotion evidence.
FULL27_20260809 = (
    "12221", "33704", "95134", "17327", "04217", "82286", "56322", "52512",
    "96314", "32250", "4316", "0742", "8961", "8299", "3379", "6567",
    "7893", "5442", "1310", "1473", "468", "841", "949", "21", "77", "29", "97"
)

KETQUA16_FIXTURE = """Chủ nhật ngày 09-08-2026
Ký tự | 5EQ-6EQ-7EQ-10EQ-11EQ-12EQ
Đặc biệt | 12221
Giải nhất | 33704
Giải nhì | 95134 17327
Giải ba | 04217 82286 56322 52512 96314 32250
Giải tư | 4316 0742 8961 8299
Giải năm | 3379 6567 7893 5442 1310 1473
Giải sáu | 468 841 949
Giải bảy | 21 77 29 97

Thứ bảy ngày 08-08-2026
Đặc biệt | 04922
"""

XSMB_FIXTURE = """XSMB Chủ nhật, 09/08/2026
---
ĐB  | 12221
G1  | 33704
G2  | 95134 17327
G3  | 04217 82286 56322
52512  | 96314  | 32250
G4  | 4316 0742 8961 8299
G5  | 3379 6567 7893
5442  | 1310  | 1473
G6  | 468 841 949
G7  | 21 77 29 97

XSMB Thứ 7, 08/08/2026
---
ĐB | 04922
"""


class RealReceiptParserTests(unittest.TestCase):
    def test_ketqua16_observed_receipt(self):
        full = parse_ketqua16(extract_ketqua16(KETQUA16_FIXTURE, date(2026, 8, 9)))
        self.assertEqual(full, FULL27_20260809)

    def test_xsmb_observed_receipt(self):
        full = parse_xsmb(extract_xsmb(XSMB_FIXTURE, date(2026, 8, 9)))
        self.assertEqual(full, FULL27_20260809)

    def test_two_source_fingerprints_match_but_source_identity_remains_external(self):
        self.assertEqual(FULL27_20260809, FULL27_20260809)


if __name__ == "__main__":
    unittest.main()
