# AI PROGRESS LEDGER V1 — MANDATORY CONTINUATION PROTOCOL

## Purpose

This is operational memory, not a summary. Every Bot MUST read it before acting and update it after acting. A future Bot must continue from the recorded state, evidence, and NEXT_ACTION rather than reconstructing intent from conversation memory.

## Current state

```text
DATA FOUNDATION = INCOMPLETE
FULL_27 = IMPLEMENTED
TAIL_27 = DERIVED_ONLY / LOCKED
CALENDAR = LOCKED
SOURCE REGISTRY = 4 SOURCES
CONTENT HYGIENE = IMPLEMENTED
CANDIDATE EVIDENCE = IMPLEMENTED
BRAIN GOVERNANCE = ACTIVE
UI PRESERVATION = LOCKED
RUNTIME HISTORICAL SLICE = NOT YET VERIFIED
PROMOTION = DENY
```

## Mandatory continuation protocol

Before work:

1. Read `docs/AI_START_HERE.md`.
2. Read `docs/DATA_FOUNDATION_BLUEPRINT_V1.md`.
3. Read this ledger completely.
4. Read `docs/AI_ACTION_LOG_V1.md`.
5. Inspect latest Git commits and relevant files.
6. Resume from `NEXT_ACTION`.

After work:

1. Record the exact action.
2. Record exact files changed.
3. Record commit SHA(s).
4. Record static verification.
5. Record runtime verification separately.
6. Record evidence artifacts/hashes.
7. Record failures and unknowns.
8. Record governance decision.
9. Update CURRENT STATE.
10. Replace NEXT_ACTION with the next concrete action.
11. Add the same event to the append-only action history.

Never claim execution because code merely exists.

## Evidence states

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

These states are not interchangeable.

## Existing completed work

- Repository reset and foundation established.
- FULL_27 canonical topology established: DB1x5, G1 1x5, G2 2x5, G3 6x5, G4 4x4, G5 6x4, G6 3x3, G7 4x2 = 27 values.
- TAIL_27 is derived from FULL_27 only.
- Legacy Excel measured: 4,172 rows in its observed window; it is reconciliation reference, not full-result truth.
- 70 historical gaps identified; missing != non-draw.
- COVID interval treated as evidence candidate, not inferred truth.
- Calendar states established: DRAW_EXPECTED, DRAW_CONFIRMED, NON_DRAW_DAY, UNKNOWN_GAP.
- Four sources registered: minhngoc, xoso, xskt, ketqua16.
- Minimum independent quorum: 2; conflicts DENY.
- Content hygiene isolates ads/scripts/navigation without modifying raw bytes.
- Candidate evidence contract forces promotion=DENY.
- Historical backfill planner exists.
- Project Brain governance is active.
- Legacy app.py UI preservation boundary documented.
- Foundation blueprint/runbook/tree/AI handoff documents exist.
- This ledger and action log now form the persistent continuation memory.

## Current NEXT_ACTION

### N001 — Real ingestion layer

Implement and verify, in this exact order:

1. Four source-specific adapters:
   - minhngoc
   - xoso
   - xskt
   - ketqua16
2. Common `CandidateRecord` output contract.
3. Immutable SHA-addressed raw artifact persistence.
4. Adversarial fixtures:
   - ads around table;
   - banners containing numbers;
   - scripts containing numbers;
   - navigation containing numbers;
   - duplicate tables;
   - malformed prize widths;
   - wrong-date page;
   - missing prize group.
5. Universal FULL_27 validator over all adapters.
6. Bounded real historical slice on Render.
7. Capture runtime evidence and hashes.
8. Compare derived TAIL_27 with legacy Excel reference.
9. Record all outcomes here and in action log.
10. Only then expand historical backfill.

## Handoff template

```text
DATE/TIME:
BOT/ACTOR:
ACTION_ID:
OBJECTIVE:
FILES_CHANGED:
COMMIT_SHA:
STATIC_VERIFICATION:
RUNTIME_VERIFICATION:
EVIDENCE_ARTIFACTS:
FAILURES / UNKNOWN:
GOVERNANCE_DECISION:
CURRENT_STATE:
NEXT_ACTION:
```

## Forbidden continuation behavior

A future Bot MUST NOT:

- restart the architecture because it lacks conversational memory;
- create a second competing data pipeline;
- replace FULL_27 with TAIL_27;
- use Excel tails to reconstruct missing full results;
- classify missing dates as non-draw without evidence;
- bypass source registry, provenance, content hygiene, calendar or quorum;
- let advertisements become data;
- let Brain invent, silently repair, or overwrite source truth;
- call static inspection runtime verification;
- promote candidate evidence automatically;
- redesign preserved UI while foundation is incomplete;
- delete or overwrite forensic evidence to make tests pass;
- erase prior ledger/action history.

## Completion gate

`DATA FOUNDATION = COMPLETE` only when all blueprint completion criteria are evidenced. Until then:

```text
DATA FOUNDATION = INCOMPLETE
PROMOTION = DENY
```
