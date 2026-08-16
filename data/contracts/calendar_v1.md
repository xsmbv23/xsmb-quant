# CALENDAR / DRAW-STATE CONTRACT V1

The calendar is authoritative for whether a date is expected to contain a draw.

## States

- `DRAW_EXPECTED`: a draw should exist, but evidence has not yet been confirmed.
- `DRAW_CONFIRMED`: a valid FULL_27 record has been independently confirmed.
- `NON_DRAW_DAY`: an officially documented no-draw date.
- `UNKNOWN_GAP`: missing evidence with no authoritative non-draw explanation.

## Non-negotiable rule

`missing data != NON_DRAW_DAY`.

A crawler must never manufacture a non-draw state merely because a source returned no result.

## Historical handling

The calendar ledger must explicitly represent exceptional periods, including Tet/New Year closures and the 2020 COVID-19 lottery suspension/resumption period. These are calendar facts to be evidenced and versioned, not inferred from weekday logic.

## Backfill rule

A legacy dataset ending at a historical watermark is not assumed complete. The runner reconciles:

`legacy data -> calendar ledger -> source evidence -> canonical FULL_27`.

Unknown gaps remain unresolved and block canonical promotion until evidence is obtained.
