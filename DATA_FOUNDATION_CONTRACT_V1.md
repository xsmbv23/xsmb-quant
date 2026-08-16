# DATA FOUNDATION CONTRACT V1

1. Raw source bytes are preserved and hashed before parsing.
2. Canonical truth is FULL_27, never TAIL_27.
3. Prize structure is exactly `1,1,2,6,4,6,3,4` for DB/G1/G2/G3/G4/G5/G6/G7.
4. TAIL_27 is derived only after FULL_27 validation.
5. A source/day is accepted canonically only with quorum >= 2 independent domains.
6. Conflicting full-prize variants are recorded in a conflict ledger and are never silently overwritten.
7. The legacy `Ket_Qua_Loto27.xlsx` remains a reconciliation reference only.
8. No runtime database, Google Sheets, Render service, or UI is required for the data foundation to be verified.
