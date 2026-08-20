# AI PROGRESS LEDGER V1 — MANDATORY CONTINUATION PROTOCOL

## Purpose

This is operational memory, not a summary. Every Bot MUST read it before acting and update it after acting. A future Bot must continue from the recorded state, evidence, and NEXT_ACTION rather than reconstructing intent from conversation memory.

## Current state

```text
DATA FOUNDATION = INCOMPLETE
FULL_27 = IMPLEMENTED
TAIL_27 = DERIVED_ONLY / LOCKED
CALENDAR = LOCKED
SOURCE REGISTRY = 5 SOURCES
ACQUISITION REGISTRY PARITY = IMPLEMENTED / STATIC CONTRACT TESTED
KETQUA16 ADAPTER = IMPLEMENTED / STATIC TESTED
XSMB ADAPTER = EXISTING / WIRED INTO MAIN CRAWLER
CONTENT HYGIENE = IMPLEMENTED
CANDIDATE EVIDENCE = IMPLEMENTED
BRAIN GOVERNANCE = ACTIVE
COMMUNICATION SECURITY = RUNTIME_VERIFIED
LAYER / CORRIDOR MATRIX = RUNTIME_VERIFIED
CAPABILITY AUTHORITY = RUNTIME_VERIFIED
COMMUNICATION AUDIT = RUNTIME_VERIFIED
RAW ARTIFACT PERSISTENCE = LOCAL WRITE-ONCE ONLY / NOT DURABLE
DURABLE DATABASE BINDING = NOT_BOUND
UI PRESERVATION = LOCKED
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

## Critical invariant: no PASS inheritance

Forensic database admission is one chain, not multiple independent Forensic systems:

```text
DB_EXISTENCE
    -> DB_BINDING
    -> DB_TLS_ADMISSION
    -> DB_ROUND_TRIP
    -> PROMOTION
```

A PASS at one gate is only a prerequisite for testing the next gate. It is never inherited upward. In particular:

```text
DATABASE_EXISTS = PASS
    !=
SERVICE_AUTHORIZED = PASS

BOUND_TLS = PASS
    !=
DURABLE_EVIDENCE = PASS

WRITE_READ_HASH_MATCH = PASS
    -> may satisfy the durable evidence gate
```

`UNKNOWN` is never converted to PASS by inference.

## Source registry / acquisition drift rule

The authoritative registry currently contains five sources:

```text
minhngoc
xoso
xskt
ketqua16
xsmb
```

The main forensic crawler must derive its default source set from `source_registry_v2.json`. It must reject explicitly requested source IDs that are not registered.

Current acquisition routes:

```text
minhngoc -> generic date URL
xoso     -> generic date URL
xskt     -> generic date URL
ketqua16 -> data/ingestion/ketqua16_source_d.py
xsmb     -> data/ingestion/xsmb_source_b.py
```

`ketqua16.net` is a registered independent publisher and is part of the current primary real-source pair with `xsmb.com.vn` for quorum work. The source registry and crawler are now statically guarded against silent source-list drift.

## Content hygiene invariant

Advertisements, banners, scripts, navigation, analytics, sponsored blocks and other non-result content are never canonical. Raw forensic bytes remain untouched. Parsing must operate on an isolated visible-content representation or an explicit result panel. A website containing advertising is not itself unsafe; the unsafe operation is allowing advertising/navigation/script content to influence FULL_27 extraction.

## Raw durability invariant

`runtime/raw` is a write-once local capture cache. It preserves raw bytes and SHA-256, but it is explicitly marked:

```text
durability = LOCAL_EPHEMERAL
promotion_eligible = false
```

The local filesystem is never allowed to masquerade as durable forensic storage. Durable admission requires an explicit durable sink and a real write -> read -> SHA-256 match.

## Existing completed work

- Repository reset and foundation established.
- FULL_27 canonical topology established: DB1x5, G1 1x5, G2 2x5, G3 6x5, G4 4x4, G5 6x4, G6 3x3, G7 4x2 = 27 values.
- TAIL_27 is derived from FULL_27 only.
- Legacy Excel measured: 4,172 rows in its observed window; it is reconciliation reference, not full-result truth.
- 70 historical gaps identified; missing != non-draw.
- COVID interval treated as evidence candidate, not inferred truth.
- Calendar states established: DRAW_EXPECTED, DRAW_CONFIRMED, NON_DRAW_DAY, UNKNOWN_GAP.
- Five sources registered: minhngoc, xoso, xskt, ketqua16, xsmb.
- Minimum independent quorum: 2; conflicts DENY.
- Content hygiene isolates ads/scripts/navigation without modifying raw bytes.
- Candidate evidence contract forces promotion=DENY.
- Historical backfill planner exists.
- Project Brain governance is active.
- Legacy app.py UI preservation boundary documented.
- Foundation blueprint/runbook/tree/AI handoff documents exist.
- Fosennic system closure map exists and treats the architecture as a graph with feedback loops and fail-closed branches.
- Communication security is explicitly modeled as room-to-room corridor crossing with layer classification, authorization, capability, lineage and audit requirements.
- N002 runtime security primitives implemented: message envelope, corridor gate, capability authority, communication audit and invariant tests.
- N003 runtime verification completed on Render: replay, unknown corridor, missing lineage, capability scope mismatch, capability replay, append-only audit, secret redaction and terminal-halt fail-closed all verified.
- N004 first registered source (`minhngoc`) executed through the L0 adapter on Render.
- N004 captured raw HTTP bytes before extraction, SHA-256 bound the raw source, applied content hygiene, extracted exactly 27 FULL_27 values with leading zeros preserved, and kept promotion denied.
- N005 persistence implementation was added with TLS-required PostgreSQL, immutable raw bytes, provenance and idempotency constraints.
- N005 runtime gate correctly failed closed because `DATABASE_URL` is not bound to the Render service.
- N005 persistence flag was returned to `0`; the service is not intentionally left in a failing persistence mode.
- N062 established the credential-free Render database binding contract and runtime probe. Exact-current runtime reported `NOT_BOUND`; no credential was fabricated or stored.
- Proactive audit identified source-registry -> acquisition implementation drift.
- Main crawler was changed to registry-driven acquisition and wired to the existing `xsmb` adapter plus a new `ketqua16` adapter.
- `ketqua16_source_d.py` performs bounded streaming capture and target-date block extraction before FULL_27 validation.
- Registry/acquisition parity tests were added.
- Raw local capture metadata now explicitly declares `LOCAL_EPHEMERAL` and `promotion_eligible=false` in the new store implementation.
- README was corrected from the stale four-source statement to the authoritative five-source registry.

## Current NEXT_ACTION

### N064 — Static + bounded real-source acquisition verification

1. Run the registry parity tests and ketqua16 parser tests.
2. Run a bounded real-source probe for `ketqua16` and `xsmb` for one already-observed historical date where both sources should contain the result.
3. Record raw SHA-256, source URL, observed date, FULL_27 fingerprint and parser status only; never record credentials.
4. Verify both sources independently produce 27 values with strict widths.
5. Verify the two source records remain separate evidence objects and are not merged before quorum.
6. Measure memory during the probe; keep worker count bounded and never load multi-day history into one process.
7. Do not promote the result. The target output is `CANDIDATE` evidence only.
8. If either source fails, classify the exact failure and keep the quorum gate DENY.
9. After N064, address durable raw evidence binding separately; local runtime/raw remains non-durable.

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
- treat ephemeral raw captures as immutable durable evidence;
- log credentials, DATABASE_URL, tokens or capability secrets;
- treat a registry entry as proof that its collector works;
- treat a collector PASS as canonical truth;
- inherit PASS from one Forensic admission gate to another.

## Completion gate

`DATA FOUNDATION = COMPLETE` only when all blueprint completion criteria are evidenced AND all required cross-room communication paths are registered, enforced and runtime-verified. Until then:

```text
DATA FOUNDATION = INCOMPLETE
PROMOTION = DENY
```