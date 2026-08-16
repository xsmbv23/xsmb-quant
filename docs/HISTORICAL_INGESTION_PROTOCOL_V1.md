# Historical Ingestion Protocol V1

Historical reconstruction is evidence collection, not canonical mutation.

## Sequence

1. Calendar planner selects `DRAW_EXPECTED` dates only.
2. Source registry expands the date into source-specific URLs.
3. Each HTTP response is persisted as a write-once raw artifact before parsing.
4. Raw bytes receive SHA-256 identity and retrieval metadata.
5. Parser extracts FULL_27 without reducing values to tails.
6. Each source observation is independently validated.
7. Reconciliation groups observations by exact FULL_27 tuple.
8. Fewer than two independent sources => `DENY`.
9. Any source conflict => retain all observations and `DENY`.
10. Only a conflict-free quorum becomes `CANONICAL_CANDIDATE`.
11. Project_Brain policy evaluates the candidate.
12. Promotion remains a separate later operation.

## Failure semantics

Network failure, parser failure, calendar uncertainty, source conflict, malformed prize width, or insufficient quorum never produces a fabricated row.

## Important

This protocol does not use `Ket_Qua_Loto27.xlsx` to reconstruct missing FULL_27 values. The legacy Excel dataset is used only after FULL_27 extraction to compare derived TAIL_27 values.
