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
COMMUNICATION SECURITY = SPECIFIED / NOT YET RUNTIME ENFORCED
LAYER / CORRIDOR MATRIX = SPECIFIED / NOT YET RUNTIME ENFORCED
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
7. Read `docs/AI_ACTION_LOG_V1.md`.
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
- Fosennic system closure map exists and treats the architecture as a graph with feedback loops and fail-closed branches.
- Communication security is now explicitly modeled as room-to-room corridor crossing with layer classification, authorization, capability, lineage and audit requirements.
- Layer/corridor matrix exists with default DENY.
- This ledger and action log form the persistent continuation memory.

## Current NEXT_ACTION

### N002 — Security enforcement before broad ingestion

Implement and verify the communication boundary primitives before allowing the four source adapters to become a connected runtime graph:

1. Define `RoomIdentity` / layer identity.
2. Define corridor registry from `docs/FOSENNIC_LAYER_CORRIDOR_MATRIX_V1.md`.
3. Define a strict message envelope with schema/version/lineage/state.
4. Implement default-DENY corridor authorization.
5. Implement privileged capability issuance/consumption using the existing forensic capability pattern.
6. Implement pre/post identity checks and anti-TOCTOU checks.
7. Implement append-only communication audit events with secret redaction.
8. Implement fail-closed handling: privileged security failure -> TERMINAL_HALT; ordinary data-gate failure -> DENY/HOLD according to the contract.
9. Add invariant tests for forbidden privilege inversions.
10. Only after these gates pass, connect the four source adapters into the runtime graph.

### Why this is before the crawler

The crawler is a lower-trust L0 component. If it is connected directly to higher layers before the corridor model exists, the system can accidentally create an ungoverned privilege path. Fosennic requires the corridors to exist before the rooms are connected.

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
- log credentials, DATABASE_URL, tokens or capability secrets.

## Completion gate

`DATA FOUNDATION = COMPLETE` only when all blueprint completion criteria are evidenced AND all required cross-room communication paths are registered and fail-closed. Until then:

```text
DATA FOUNDATION = INCOMPLETE
COMMUNICATION SECURITY = INCOMPLETE
PROMOTION = DENY
```
