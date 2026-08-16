# FOSENNIC SYSTEM CLOSURE MAP V1

## Purpose

The data-foundation blueprint is **not** the whole system architecture. This document closes that gap.
It maps the cross-subsystem dependencies, branch points, feedback loops and fail-closed gates from raw data through UI, Quant, risk, audit, Brain and future promotion.

## A. Whole-system topology

```text
                         +----------------------+
                         |  EXTERNAL SOURCES    |
                         |  4+ independent     |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | RAW / PROVENANCE     |
                         | bytes + SHA + time   |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | DATA FOUNDATION      |
                         | calendar/content/    |
                         | parser/FULL_27       |
                         +----------+-----------+
                                    |
                    +---------------+----------------+
                    |                                |
                    v                                v
             RECONCILIATION                    DATA QUALITY
             Excel reference                  missing/conflict/
             TAIL_27 compare                  date integrity
                    |                                |
                    +---------------+----------------+
                                    |
                                    v
                         +----------------------+
                         | TEMPORAL SNAPSHOT    |
                         | as-of date only      |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | FEATURE / SIGNAL     |
                         | Alpha sensors        |
                         | Prob_T3 / regime     |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | QUANT DECISION CORE  |
                         | scoring / strategies |
                         | sizing / MM          |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | RISK / SAFEGUARDS    |
                         | temporal / OOS /     |
                         | circuit breakers     |
                         +----------+-----------+
                                    |
                           +--------+--------+
                           |                 |
                           v                 v
                     TRADE DECISION     TRADE SKIP
                           |                 |
                           +--------+--------+
                                    |
                                    v
                         +----------------------+
                         | IMMUTABLE DECISION   |
                         | / PERFORMANCE LEDGER |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | AUDIT / REPORTING    |
                         +----------+-----------+
                                    |
                    +---------------+----------------+
                    |                                |
                    v                                v
                 UI REPORT                     NEXT-DAY STATE
                    |                                |
                    +---------------+----------------+
                                    |
                                    v
                         +----------------------+
                         | PROJECT_BRAIN_AI     |
                         | GOVERNANCE / INVARIANT|
                         +----------+-----------+
                                    |
                   +----------------+----------------+
                   |                                 |
                   v                                 v
                 DENY                         CANDIDATE / HOLD
                   |                                 |
                   +----------------+----------------+
                                    |
                                    v
                         +----------------------+
                         | EXPLICIT PROMOTION   |
                         | GATE (future)        |
                         +----------------------+
                                    |
                              PASS / DENY
```

## B. Critical branch points

### B1 — Source acquisition

```text
HTTP / source
  |
  +-- unavailable --> FETCH_FAILED --> UNKNOWN --> DENY
  |
  +-- HTTP 200 but wrong date --> DATE_MISMATCH --> DENY
  |
  +-- content contaminated --> isolate AD/SCRIPT/NAV; retain RAW
  |
  +-- candidate table --> parser
```

### B2 — FULL_27 validation

```text
candidate
  |
  +-- malformed --> FULL_27_INVALID --> DENY
  |
  +-- valid --> calendar gate
```

### B3 — Calendar

```text
requested date
  |
  +-- authoritative draw evidence --> DRAW_CONFIRMED
  |
  +-- authoritative closure evidence --> NON_DRAW_DAY
  |
  +-- no sufficient evidence --> UNKNOWN_GAP --> HOLD / DENY
```

Holiday/Tết and COVID are evidence cases, not hard-coded assumptions.

### B4 — Cross-source quorum

```text
sources
  |
  +-- <2 independent --> QUORUM_FAIL --> DENY
  |
  +-- >=2 but disagree --> SOURCE_CONFLICT --> conflict ledger --> DENY
  |
  +-- >=2 agree --> provenance verified
```

### B5 — Temporal snapshot

No future record may enter an as-of snapshot. The historical snapshot must be isolated before any feature, score or prediction calculation.

### B6 — Quant decision

The signal layer can produce a candidate decision but cannot bypass safeguards, risk controls or Brain governance.

### B7 — Safeguard branch

Any temporal, OOS, data-quality, circuit-breaker or integrity failure routes to SKIP/DENY rather than being repaired silently.

## C. Fosennic feedback loops

### C1 — Data correction loop

```text
SOURCE
  -> candidate
  -> validator
  -> conflict / UNKNOWN
  -> evidence investigation
  -> source/calendar correction
  -> re-fetch / re-validate
  -> new evidence version
```

This is an **evidence loop**, not a mutation loop. Old evidence is retained.

### C2 — Quant audit loop

```text
prediction
  -> decision
  -> immutable decision ledger
  -> realized outcome
  -> performance audit
  -> research evidence
  -> versioned model/policy candidate
  -> verification
```

No live policy may be rewritten from the audit loop without a separate promotion gate.

### C3 — Brain governance loop

```text
all subsystem outputs
        -> Brain observes
        -> invariant evaluation
        -> DENY / HOLD / CANDIDATE
        -> evidence ledger
        -> next controlled action
```

Brain is a governor, not a hidden second data engine.

### C4 — Runtime state-machine loop

The historical forensic runtime architecture already uses monotonic state transitions such as:

```text
LOCKED
  -> VACCINE_PASS
  -> PRE_HOLDOUT_EXECUTED
  -> PROMOTION_PASS
  -> CAPABILITY_ISSUED
  -> HOLDOUT_MATERIALIZED
```

Illegal transitions must halt. This pattern must be reused for the new foundation/promotion lifecycle instead of using loose boolean flags.

## D. Dependency direction

Allowed direction:

```text
DATA
 -> TEMPORAL SNAPSHOT
 -> FEATURES
 -> QUANT
 -> RISK / SAFEGUARDS
 -> DECISION
 -> AUDIT
 -> BRAIN GOVERNANCE
 -> PROMOTION
```

Forbidden reverse dependencies:

```text
UI -> DATA truth
Brain -> raw source mutation
TAIL_27 -> FULL_27
Prediction -> historical data repair
Audit -> live policy mutation
Promotion -> bypass validator
Render -> canonical truth
```

## E. Existing legacy architecture evidence to preserve

The historical codebase demonstrates important links that must not be lost:

- `DatabaseManager` establishes database boundaries and next prediction date.
- `TemporalSnapshot` supplies as-of historical state to the Quant engine.
- `QuantEngine.get_full_prediction()` consumes the snapshot rather than arbitrary future/global state.
- `QuantEngine.get_mm_multiplier()` participates in sizing/circuit logic.
- `ImmutableDecisionLedger` records decisions with snapshot hashes.
- `Auditor` routes single-day/monthly forensic analysis and reports synchronization state.
- Manifest/frozen-policy structures bind the live path to explicit policy versions.
- Runtime vaccine/holdout state machines demonstrate monotonic capability issuance.

These are architectural relationships, not merely implementation details.

## F. New foundation must connect to old architecture at explicit interfaces

```text
NEW DATA FOUNDATION
        |
        +--> Canonical FULL_27 / date / provenance
                         |
                         v
                 DATABASE / CANONICAL STORE
                         |
                         v
                 TemporalSnapshot interface
                         |
                         v
                  existing Quant core
                         |
                         v
                 existing Audit/ledger
                         |
                         v
                    Brain governance
                         |
                         v
                   preserved app.py UI
```

No direct shortcut from crawler to UI, crawler to Quant, or AI to database truth.

## G. Upgrades recommended before closing the foundation

1. **Canonical system state machine** — replace scattered booleans with explicit monotonic states and terminal DENY/HALT.
2. **Provenance propagation** — every FULL_27 record must carry source SHA, parser version, calendar evidence ID and reconciliation status into downstream snapshots.
3. **Dependency manifest** — machine-readable DAG of modules, allowed inputs and forbidden outputs.
4. **Invariant test matrix** — every branch above becomes a testable invariant.
5. **Decision-ledger linkage** — every Quant decision references the exact data snapshot hash and policy manifest hash.
6. **Evidence versioning** — corrections create new evidence versions; old evidence is never overwritten.
7. **UI/Core adapter boundary** — app.py receives stable service interfaces and cannot reach raw ingestion directly.
8. **Brain veto boundary** — Brain can veto/hold, but cannot manufacture or silently mutate source truth.
9. **Promotion firewall** — promotion requires all prerequisite evidence states, not a single PASS flag.
10. **Observability graph** — each runtime failure should identify the exact node and upstream evidence chain that caused the DENY.

## H. Foundation completion is now a graph condition

The data foundation is not complete merely because the crawler works.
It is complete only when every required node has a valid upstream/downstream contract and every branch terminates safely.

```text
FOUNDATION COMPLETE iff:
  every input has provenance
  AND every candidate has validation
  AND every date has calendar state
  AND every canonical candidate has quorum
  AND every downstream snapshot carries lineage
  AND every decision is reproducible from snapshot + policy
  AND every failure path terminates DENY/HOLD
  AND every feedback loop is append-only/versioned
  AND UI cannot bypass the core
  AND Brain cannot bypass evidence
```

Until then:

`DATA FOUNDATION = INCOMPLETE`

`PROMOTION = DENY`
