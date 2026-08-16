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
COMMUNICATION SECURITY = RUNTIME_VERIFIED
LAYER / CORRIDOR MATRIX = RUNTIME_VERIFIED
CAPABILITY AUTHORITY = RUNTIME_VERIFIED
COMMUNICATION AUDIT = RUNTIME_VERIFIED
UI PRESERVATION = LOCKED
RUNTIME HISTORICAL SLICE = NOT YET VERIFIED
PROMOTION = DENY
```

## Mandatory continuation protocol

Before work:

1. Read `docs/AI_START_HERE.md`.
2. Read `docs/DATA_FOUNDATION_BLUEPRINT_V1.md`.
3. Read `docs/FOSENNIC_SYSTEM_CLOSURE_MAP_V1.md`.
4. Read `docs/FOSENNIC_COMMUNICATION_SECURITY_V1.md`.
5. Read `docs/FOSENNIC_LAYER_CORRIDOR_MATRIX_V1.md`.
6. Read this ledger completely.
7. Read `docs/AI_ACTION_LOG_V1.md` and the newest files under `docs/action_log/`.
8. Inspect latest Git commits and relevant files.
9. Resume from `NEXT_ACTION`.

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
- FULL_27 canonical topology established: DB1x5, G1 1x5, G2 2x5, G3 6x5, G4 4x5, G5 6x4, G6 3x3, G7 4x2 = 27 values.
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
- Fosennic system closure map exists and treats the architecture as a graph with feedback loops and fail-closed branches.
- Communication security is explicitly modeled as room-to-room corridor crossing with layer classification, authorization, capability, lineage and audit requirements.
- Layer/corridor matrix exists with default DENY.
- N002 runtime security primitives implemented: message envelope, corridor gate, capability authority, communication audit and invariant tests.
- N003 runtime verification completed on Render: replay, unknown corridor, missing lineage, capability scope mismatch, capability replay, append-only audit, secret redaction and terminal-halt fail-closed all verified.
- N003 evidence bound under `evidence/runtime/N003_security_runtime_verification_v2.json`.
- Persistent action record for N003 created under `docs/action_log/`.
- This ledger and action log form the persistent continuation memory.

## Current NEXT_ACTION

### N004 — First bounded source adapter through the security corridor

Do not connect all four sources simultaneously. Start with exactly one source adapter as the controlled L0→L1 path:

1. Select the first registered source from `data/ingestion/source_registry_v2.json` according to the existing registry order/policy.
2. Build an adapter that captures raw response bytes without modifying them.
3. Record source URL, retrieval timestamp, HTTP metadata, content hash and parser version.
4. Pass the captured artifact through content hygiene before any extraction.
5. Emit only a schema-validated `RAW_SOURCE_V1` envelope through the registered L0→L1 corridor.
6. Store raw evidence immutably; never overwrite a prior capture.
7. Parse FULL_27 only after provenance is bound.
8. Never derive TAIL_27 from source HTML when FULL_27 is available.
9. Run a bounded fixture first; then a single real retrieval.
10. Compare the extracted result against an independent reference before widening the source.
11. Record runtime evidence and exact hashes.
12. Keep `PROMOTION = DENY`.

### Why this is the next gate

The security corridor is now runtime-proven. The next risk is the L0 data ingress itself: advertisements, navigation, malformed pages, changed HTML, missing dates, duplicate captures and parser drift must be contained before multiple sources can interact. One source at a time preserves forensic causality.

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
- erase prior ledger/action history;
- create direct cross-room calls without a registered corridor;
- allow lower-layer components to issue upper-layer capabilities;
- allow UI/reporting to mutate canonical truth;
- connect all source adapters at once;
- log credentials, DATABASE_URL, tokens or capability secrets.

## Completion gate

`DATA FOUNDATION = COMPLETE` only when all blueprint completion criteria are evidenced AND all required cross-room communication paths are registered, enforced and runtime-verified. Until then:

```text
DATA FOUNDATION = INCOMPLETE
PROMOTION = DENY
```
