# Legacy reference fixture

The original `Ket_Qua_Loto27.xlsx` is retained outside Git source control as a data artifact.

Observed artifact SHA-256:

`48e0251d8fe4e986579a118c9372ae1b2289e6ca1b67884df5827e692426f94f`

Observed structure:

- rows: 4,172 data rows + header
- date range: 2015-01-01 through 2026-08-12
- every row contains exactly 27 two-digit tails
- this is **legacy derived data**, not canonical FULL_27 truth

The artifact must be supplied to verification jobs by an explicit fixture path. It is never fetched from runtime or silently regenerated.
