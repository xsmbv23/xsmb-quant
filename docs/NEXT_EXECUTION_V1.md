# NEXT EXECUTION V1

The next executable phase is historical FULL_27 reconstruction.

## Order

1. Load legacy `Ket_Qua_Loto27.xlsx` only as a reconciliation reference.
2. Build the calendar evidence ledger for all 70 historical gaps.
3. Keep unresolved gaps as `UNKNOWN_GAP`.
4. For every confirmed draw date, fetch at least two independent sources.
5. Preserve raw source bytes and SHA256 before parsing.
6. Extract strict FULL_27.
7. Reconcile derived TAIL_27 against the legacy row when present.
8. Retain conflicts; never silently choose a winner.
9. Ask Project_Brain governance for promotion decision.
10. Persist canonical data only after every mandatory gate passes.

## Prohibited shortcuts

- no synthetic prize values;
- no weekday-only calendar inference;
- no conversion of missing data into non-draw;
- no tail-only canonical dataset;
- no overwrite of conflicting source variants;
- no production mutation from the crawler;
- no Render startup hydration from a legacy spreadsheet.

`IMPLEMENTED != VERIFIED != PROMOTED`.
