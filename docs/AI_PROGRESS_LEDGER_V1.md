# AI PROGRESS LEDGER V1 — MANDATORY CONTINUATION PROTOCOL

## Purpose

This file is not a project summary. It is an **operational memory protocol**.
Every AI/Bot that changes this repository MUST update this ledger in the same change set so the next AI can continue from the exact state reached by the previous AI.

## Mandatory rule

Before doing any work:

1. Read `docs/AI_START_HERE.md`.
2. Read `docs/DATA_FOUNDATION_BLUEPRINT_V1.md`.
3. Read this ledger from top to bottom.
4. Inspect the repository state and the latest commits.
5. Continue from `CURRENT_STATE` and `NEXT_ACTION`, not from assumptions.

After doing work:

1. Record what was actually changed.
2. Record what was actually verified.
3. Record what failed or remains unknown.
4. Record exact commit SHA(s).
5. Record Render deployment state if Render was touched.
6. Update `CURRENT_STATE`.
7. Replace `NEXT_ACTION` with the next concrete action.
8. Never claim an action was executed if only code was written.

## Current state

### Foundation

- DATA FOUNDATION: INCOMPLETE
- FULL_27 canonical topology: IMPLEMENTED
- TAIL_27 derivation: LOCKED
- Calendar UNKNOWN_GAP rule: LOCKED
- Source registry: 4 sources registered
- Content hygiene / ad isolation: IMPLEMENTED
- Candidate evidence contract: IMPLEMENTED
- Brain governance boundary: IMPLEMENTED
- UI preservation boundary: DOCUMENTED
- Promotion: DENY

### Registered sources

1. minhngoc
2. xoso
3. xskt
4. ketqua16

Minimum independent quorum: 2.

### Legacy reference

`Ket_Qua_Loto27.xlsx` is reconciliation reference only.
It contains 4,172 historical rows and 27 two-digit tails per row.
The Excel tails must never be used to reconstruct missing full prize values.

### Historical gaps

70 gaps were identified in the legacy window.
COVID-era 2020-04-01 through 2020-04-22 is treated as a candidate non-draw interval, not automatically as truth. Calendar evidence must bind it before canonical classification.

### Runtime

Render is an execution boundary only.
GitHub is code/governance/version control.
Postgres is persistence when the data layer is ready.
Raw source artifacts are immutable provenance.

## Completed work history

### Phase 0 — Repository reset / foundation rebuild

- New repository: `xsmbv23/xsmb-quant`.
- Render service: `srv-da0obdpt0dsc73a5ubbg`.
- Promotion intentionally disabled.

### Phase 1 — Contracts and governance

Implemented/locked:

- FULL_27 contract.
- Calendar contract.
- Project_Brain governance contract.
- Canonical verification runner concept.
- Candidate evidence separation.
- Legacy UI preservation contract.

### Phase 2 — Historical measurement

Verified from legacy Excel:

- 4,172 rows.
- historical range measured from workbook.
- 70 missing-date gaps.
- gaps are UNKNOWN until evidence says otherwise.
- COVID suspension interval identified as a special evidence candidate.

### Phase 3 — Ingestion architecture

Implemented:

- source registry V2;
- four registered sources;
- content hygiene boundary;
- source-specific parser architecture;
- universal FULL_27 validation;
- raw provenance requirement;
- quorum/conflict policy;
- historical backfill planner;
- candidate evidence schema.

### Phase 4 — AI handoff

Created:

- `docs/DATA_FOUNDATION_BLUEPRINT_V1.md`
- `docs/DATA_FOUNDATION_RUNBOOK_V1.md`
- `docs/DATA_FOUNDATION_TREE_V1.mermaid`
- `docs/AI_START_HERE.md`
- this ledger

## Exact operating philosophy

The previous AI must never be treated as an authority merely because it wrote code.
Only repository artifacts, test output, runtime evidence, hashes, and explicit governance states count as evidence.

Use these labels precisely:

```text
PLANNED
IMPLEMENTED
STATIC_VERIFIED
RUNTIME_VERIFIED
EVIDENCE_BOUND
PROMOTED
DENIED
UNKNOWN
```

Do not collapse them into one PASS flag.

## Next action

The next AI must:

1. Implement source-specific adapters for all four registered sources.
2. Make every adapter emit the same `CandidateRecord` shape.
3. Implement raw artifact persistence with immutable SHA-addressed storage.
4. Implement parser fixtures for ads, navigation, scripts, malformed tables, duplicated tables, and date mismatch.
5. Execute a small historical slice on Render.
6. Capture real runtime evidence.
7. Compare derived TAIL_27 against the legacy Excel reference.
8. Record every result in this ledger.
9. Only after the slice is clean, expand the historical backfill range.

## Continuation rule

When an AI completes `NEXT_ACTION`, it must update this section before starting the following action. This creates a durable chain:

```text
BOT N
  |
  +-- action
  +-- evidence
  +-- commit SHA
  +-- state update
  +-- next action
          |
          v
BOT N+1
  |
  +-- reads ledger
  +-- resumes exactly here
```

## Forbidden continuation behavior

A future AI MUST NOT:

- restart the architecture from scratch because it does not remember context;
- create a second competing data pipeline;
- replace FULL_27 with TAIL_27;
- treat Excel as canonical full-result truth;
- treat missing dates as non-draw days without evidence;
- bypass the source registry;
- bypass content hygiene;
- let ads become data;
- let Brain invent/repair values;
- declare runtime success from static code inspection;
- activate promotion merely because candidate evidence exists;
- redesign the preserved UI while data foundation is incomplete;
- delete or overwrite forensic artifacts to make tests pass.

## Ledger update template

Every meaningful action should append/update a record in this shape:

```text
DATE/TIME:
BOT/ACTOR:
ACTION:
FILES CHANGED:
COMMIT SHA:
STATIC VERIFICATION:
RUNTIME VERIFICATION:
EVIDENCE ARTIFACTS:
FAILURES / UNKNOWN:
GOVERNANCE DECISION:
CURRENT STATE:
NEXT ACTION:
```

## Final foundation handoff condition

Only when the blueprint's 14 completion criteria are all satisfied may this ledger state:

```text
DATA FOUNDATION = COMPLETE
```

Until then:

```text
DATA FOUNDATION = INCOMPLETE
PROMOTION = DENY
```
