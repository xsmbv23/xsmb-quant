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
L0 MINHNGOC ADAPTER = RUNTIME_VERIFIED / PERSISTENCE PENDING
RAW ARTIFACT PERSISTENCE = INCOMPLETE
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
- Communication security is explicitly modeled as room-to-room corridor crossing with layer classification, authorization, capability, lineage and audit requirements.
- Layer/corridor matrix exists with default DENY.
- N002 runtime security primitives implemented: message envelope, corridor gate, capability authority, communication audit and invariant tests.
- N003 runtime verification completed on Render: replay, unknown corridor, missing lineage, capability scope mismatch, capability replay, append-only audit, secret redaction and terminal-halt fail-closed all verified.
- N003 evidence bound under `evidence/runtime/N003_security_runtime_verification_v2.json`.
- N004 first registered source (`minhngoc`) executed through the L0 adapter on Render.
- N004 captured raw HTTP bytes before extraction, SHA-256 bound the raw source, applied content hygiene, extracted exactly 27 FULL_27 values with leading zeros preserved, and kept promotion denied.
- N004 evidence bound under `evidence/runtime/N004_minhnog_live_probe_v1.json`.
- N004 raw capture remains explicitly `EPHEMERAL_CAPTURE_ONLY`; immutable database persistence is not yet complete.
- Persistent action records for N002, N003 and N004 exist under `docs/action_log/`.
- This ledger and action log form the persistent continuation memory.

## Current NEXT_ACTION

### N005 — Immutable raw-artifact persistence in xsmb_runtime_db

The L0 adapter is proven against one live source, but the raw bytes are still ephemeral. Fix the foundation before widening sources.

1. Establish a TLS-required PostgreSQL client path for `xsmb_runtime_db`.
2. Add a minimal schema for immutable raw artifacts and provenance records.
3. Use a database-side unique key on `(source_id, content_sha256)` so duplicate captures are idempotent without overwriting bytes.
4. Store retrieval timestamp, URL, HTTP status, content type, raw SHA-256, byte length and parser version separately from raw bytes.
5. Store the raw bytes exactly as captured; no HTML cleanup may modify the canonical raw artifact.
6. Bind the N004 raw SHA as the first real provenance record.
7. Verify database read-after-write from the Render runtime.
8. Add a fail-closed database gate: persistence failure means `DENY/HOLD`, never “continue with unrecorded truth”.
9. Record database runtime evidence and exact hashes.
10. Keep `PROMOTION = DENY`.

### Why this is the next gate

Without immutable raw persistence, a live crawl can be observed but cannot become reproducible forensic evidence. The data foundation must therefore close the raw-artifact persistence boundary before adding xoso/xskt/ketqua16 or historical backfill.

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
- treat ephemeral raw captures as immutable evidence;
- log credentials, DATABASE_URL, tokens or capability secrets.

## Completion gate

`DATA FOUNDATION = COMPLETE` only when all blueprint completion criteria are evidenced AND all required cross-room communication paths are registered, enforced and runtime-verified. Until then:

```text
DATA FOUNDATION = INCOMPLETE
PROMOTION = DENY
```
