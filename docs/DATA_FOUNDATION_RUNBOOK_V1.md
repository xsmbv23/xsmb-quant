# DATA FOUNDATION RUNBOOK V1

## Order of execution

1. Read `DATA_FOUNDATION_BLUEPRINT_V1.md`.
2. Validate source registry.
3. Validate calendar ledger.
4. Acquire raw source bytes.
5. Hash and retain raw bytes.
6. Remove only extraction visibility of ads/scripts/navigation; never mutate raw bytes.
7. Run source-specific parser.
8. Run universal FULL_27 validator.
9. Verify page date against requested date.
10. Verify provenance and source fingerprint.
11. Resolve calendar state.
12. Require >=2 independent sources for canonical candidate.
13. Record conflicts instead of resolving them silently.
14. Derive TAIL_27 from validated FULL_27.
15. Compare derived TAIL_27 against legacy Excel.
16. Send decision to Project_Brain governance.
17. Emit candidate evidence.
18. Keep promotion DENY until the promotion layer explicitly verifies all evidence.

## Failure codes

`FETCH_FAILED`, `DATE_MISMATCH`, `AD_CONTENT_CANDIDATE`, `FULL_27_INVALID`, `CALENDAR_UNKNOWN`, `SOURCE_CONFLICT`, `QUORUM_FAIL`, `PROVENANCE_FAIL`, `LEGACY_MISMATCH`, `PROMOTION_DENY`.

## Never do

- never fabricate missing dates;
- never use synthetic values for backfill;
- never reconstruct FULL_27 from tails;
- never overwrite raw artifacts;
- never let one source override two independent sources without evidence;
- never let Brain repair source truth;
- never use Render availability as proof of data correctness;
- never call a crawler successful merely because it returned HTTP 200.
