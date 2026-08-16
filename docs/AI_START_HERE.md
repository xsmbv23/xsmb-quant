# AI START HERE — XSMB FORENSIC

If you are a new Bot/AI taking over this repository, do not start by editing application code.

## Read in this order

1. `docs/DATA_FOUNDATION_BLUEPRINT_V1.md`
2. `docs/DATA_FOUNDATION_RUNBOOK_V1.md`
3. `docs/DATA_FOUNDATION_TREE_V1.mermaid`
4. `docs/FOUNDATION_DECISIONS_V1.md`
5. `data/contracts/full27_v1.json`
6. `data/contracts/calendar_v1.md`
7. `brain/governance/PROJECT_BRAIN_GOVERNANCE_V1.md`
8. `data/ingestion/source_registry_v2.json`

## One-line architecture

`RAW SOURCE -> PROVENANCE -> CONTENT HYGIENE -> SOURCE PARSER -> FULL_27 -> CALENDAR -> QUORUM -> BRAIN -> EVIDENCE -> TAIL_27 -> RECONCILIATION -> SEPARATE PROMOTION GATE`

## Absolute constraints

- Data is the foundation.
- FULL_27 is canonical; TAIL_27 is derived.
- Missing is UNKNOWN, not NON_DRAW.
- Ads/scripts/navigation are never canonical data.
- Raw evidence is immutable.
- Conflicts are recorded, never silently repaired.
- Brain governs; it does not invent or rewrite truth.
- Render executes; it does not become truth.
- The legacy app UI is preserved.
- Promotion remains DENY until explicit evidence gates are complete.

If a proposed change violates one of these constraints, stop and redesign the change rather than weakening the constraint.
