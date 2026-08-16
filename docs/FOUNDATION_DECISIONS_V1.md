# XSMB FORENSIC — FOUNDATION DECISIONS V1

## Locked decisions

### D1 — Canonical truth
`FULL_27` is the canonical source representation. `TAIL_27` is derived and may never replace FULL_27.

### D2 — Prize structure
DB/G1/G2/G3/G4/G5/G6/G7 contain exactly 1/1/2/6/4/6/3/4 values = 27 prize values.

### D3 — Historical calendar
The system distinguishes `DRAW_EXPECTED`, `DRAW_CONFIRMED`, `NON_DRAW_DAY`, and `UNKNOWN_GAP`. Missing source data is never converted into `NON_DRAW_DAY` by inference.

### D4 — Exceptional periods
Tet/New Year closures and the 2020 COVID-19 suspension/resumption are calendar evidence to be versioned and reconciled, not inferred by weekday rules.

### D5 — Legacy Excel
`Ket_Qua_Loto27.xlsx` is a legacy tail-only reconciliation reference. It is not canonical forensic truth.

### D6 — Source preservation
Raw source bytes, source URL/domain, retrieval time and SHA256 are preserved before parsing.

### D7 — Conflict handling
Conflicting source/day variants are retained in a conflict ledger. No silent overwrite and no convenient-source selection.

### D8 — Project Brain
Project_Brain_AI participates from the foundation as governance/policy. It can observe, validate, enforce and deny; it cannot invent, repair, overwrite or promote unsupported truth.

### D9 — UI
The complete legacy `app.py` interface is preserved as the presentation contract. The backend/core is replaced behind that interface; the user-facing layout is not redesigned.

### D10 — Runtime separation
Render runtime is a consumer of promoted/persistent data. It must not crawl, rebuild canonical history, backtest or hydrate full history from Google Sheets at startup.

## Promotion rule
No foundation artifact is considered promoted merely because code exists. `IMPLEMENTED != VERIFIED != PROMOTED`.
