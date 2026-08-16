# AI START HERE — XSMB FORENSIC

If you are a new Bot/AI taking over this repository, do not start by editing application code.

## Mandatory reading order

1. `docs/DATA_FOUNDATION_BLUEPRINT_V1.md`
2. `docs/FOSENNIC_SYSTEM_CLOSURE_MAP_V1.md`
3. `docs/FOSENNIC_COMMUNICATION_SECURITY_V1.md`
4. `docs/FOSENNIC_LAYER_CORRIDOR_MATRIX_V1.md`
5. `docs/DATA_FOUNDATION_RUNBOOK_V1.md`
6. `docs/DATA_FOUNDATION_TREE_V1.mermaid`
7. `docs/FOUNDATION_DECISIONS_V1.md`
8. `docs/AI_PROGRESS_LEDGER_V1.md`
9. `docs/AI_ACTION_LOG_V1.md`
10. `data/contracts/full27_v1.json`
11. `data/contracts/calendar_v1.md`
12. `brain/governance/PROJECT_BRAIN_GOVERNANCE_V1.md`
13. `data/ingestion/source_registry_v2.json`

## Architecture invariant

`RAW SOURCE -> PROVENANCE -> DATA FOUNDATION -> TEMPORAL SNAPSHOT -> FEATURE -> QUANT -> RISK -> DECISION -> AUDIT -> BRAIN -> PROMOTION`

This is a graph, not a linear script. Every branch, feedback loop and privileged communication must obey the room/layer/corridor model.

## Room / floor rule

A subsystem is a room. A layer is a floor. Every cross-room interaction crosses a registered corridor gate.

Before any cross-room call, identify:

- source room/layer;
- destination room/layer;
- corridor type;
- schema/version;
- provenance/lineage;
- state;
- authorization;
- capability, if privileged;
- audit event;
- fail-closed destination.

Default is DENY.

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
- Lower layers provide facts/results; upper layers constrain/authorize.
- No privilege inversion.
- Every privileged corridor requires explicit authorization/capability and pre/post verification.
- Every Bot must append its action/result/next-action to the persistent progress ledger.

If a proposed change violates one of these constraints, stop and redesign the change rather than weakening the constraint.
