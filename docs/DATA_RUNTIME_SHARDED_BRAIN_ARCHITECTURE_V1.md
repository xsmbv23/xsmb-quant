# XSMB — DATA RUNTIME / SHARDED EVIDENCE / BRAIN ARCHITECTURE V1

Status: DESIGN LOCK / NOT PROMOTED
Project: XSMB_FORENSIC
Purpose: prevent Render 512 MiB OOM while preserving FULL_27 forensic truth, fast UI visibility, provenance, lineage and Fosennic fail-closed governance.

## 1. Architectural correction

The previous design correctly separated Build Plane from Render Runtime, but the legacy `app.py` still contains memory-heavy patterns that are incompatible with a 512 MiB runtime boundary:

- loading the whole dataset into a Python dictionary;
- materializing a full 100-column matrix;
- materializing full features/probabilities/regime arrays;
- maintaining request caches;
- retaining a forensic bootstrap path that can invoke the full backtest when the manifest is absent.

Moving that work to a background thread does NOT solve OOM. It only hides the expensive work behind the web server.

Therefore:

```text
UI Runtime != Audit Engine != Build Engine != Brain Governance
```

## 2. Three-plane model

### Plane A — DATA / BUILD PLANE

Heavy work only:

```text
Sources
  -> raw capture
  -> source fingerprint
  -> calendar classification
  -> FULL_27 structural validation
  -> quorum/conflict resolution
  -> immutable raw artifact
  -> canonical record
  -> chunk/shard build
  -> audit computations
  -> audit projection
  -> manifest / lineage
```

This plane may use large memory, bounded worker processes, temporary disk and batch processing. It must not be the public Gradio process.

### Plane B — PROJECT_BRAIN_AI GOVERNANCE PLANE

Brain is a separate control/governance repository and service boundary.

Brain owns:

- project registry;
- session/checkpoint continuity;
- state-version gate;
- permission gate;
- block/room locks;
- corridor authorization;
- conflict/policy gate;
- verification gate;
- mutation governance;
- promotion governance;
- action ledger;
- evidence references;
- next-action handoff.

Brain does NOT own canonical XSMB truth and does NOT become a raw-data warehouse.

It consumes compact evidence envelopes and manifests, not the entire historical dataset.

### Plane C — RENDER UI / RUNTIME PLANE

Strictly lightweight and read-oriented:

```text
PostgreSQL runtime store
  -> small query
  -> audit projection
  -> UI
```

No crawl, no historical hydration, no full backtest, no canonical rebuild, no auto-heal, no full matrix materialization on startup.

## 3. Sharding rule

The unit of fast runtime access is a `DAY_SHARD`.

One draw date is one immutable shard:

```text
DAY_SHARD_V1
  draw_date
  source_set
  calendar_state
  full_27[27]
  tail_27[27]       # derived view only
  source_hashes[]
  canonical_sha256
  shard_sha256
  provenance_id
  verification_state
  promotion_state
```

A month is a manifest over day shards.

A year is a manifest over month manifests.

The complete dataset is a root manifest over year/month/day nodes.

This produces a hierarchical evidence tree instead of one giant runtime object.

## 4. Hashing rule

Hashing is for integrity and addressing; hashing itself does NOT make computation faster.

Use:

```text
raw bytes
   -> SHA256(raw)

canonical FULL_27
   -> SHA256(canonical record)

DAY_SHARD
   -> SHA256(shard payload)

month manifest
   -> hash(children)

year manifest
   -> hash(children)

root manifest
   -> Merkle-style root hash
```

The UI never needs to recalculate the historical tree. It reads stored hashes.

## 5. Fast audit projection

The expensive audit result must be materialized separately from canonical truth.

```text
CANONICAL TRUTH
      |
      +--> immutable day shards
      |
      +--> immutable manifests
      |
      +--> audit jobs
                |
                v
        AUDIT_PROJECTION_V1
```

`AUDIT_PROJECTION_V1` contains only the values required by the UI:

- audit status;
- date/range;
- source quorum result;
- conflict count;
- data-quality state;
- temporal state;
- provenance reference;
- canonical SHA;
- relevant metrics;
- evidence references;
- computation version;
- manifest/root hash.

The UI reads this projection instead of running the audit.

## 6. Incremental audit

A new daily result must NOT trigger a complete 4,000+ day recomputation in Render.

The Build Plane processes only the affected dependency window:

```text
new DAY_SHARD
   |
   +--> structural validation
   +--> source quorum
   +--> calendar validation
   +--> day audit
   |
   +--> invalidate only dependent projections
   |
   +--> recompute bounded downstream windows
```

Historical full rebuild remains an explicit Build Plane operation.

## 7. Evidence packets sent to Brain

Brain receives a compact `EVIDENCE_ENVELOPE_V1`, for example:

```json
{
  "project_id": "XSMB_FORENSIC",
  "artifact_id": "DAY_SHARD:2026-08-15",
  "source_ids": ["minhngoc", "xoso"],
  "canonical_sha256": "...",
  "shard_sha256": "...",
  "root_manifest_sha256": "...",
  "calendar_state": "DRAW_CONFIRMED",
  "verification_state": "RUNTIME_VERIFIED",
  "promotion_state": "DENY",
  "lineage": ["raw_capture:...", "canonical:..."],
  "builder_version": "...",
  "state_version": "..."
}
```

No password, DATABASE_URL, cookies, raw credentials or unnecessary full historical payloads are sent to Brain.

## 8. Communication boundary

The existing Brain room/corridor model remains mandatory.

```text
XSMB DATA PLANE
      |
      | registered corridor: DATA_EVIDENCE_EXPORT_V1
      | capability: EVIDENCE_WRITE
      v
PROJECT_BRAIN_AI
```

Reverse direction is separately registered:

```text
PROJECT_BRAIN_AI
      |
      | registered corridor: GOVERNANCE_DECISION_READ_V1
      | capability: GOVERNANCE_READ
      v
XSMB DATA / BUILD PLANE
```

Brain must never have an implicit database-write path into canonical truth.

## 9. Render memory budget

The 512 MiB Render boundary is architectural.

Runtime rules:

- never `get_all_values()` for full history;
- never `pd.read_excel()` in production runtime;
- never build a full 100-column matrix at startup;
- never build full feature/probability arrays at startup;
- never run HMM/backtest on startup;
- never keep full raw HTML bodies after persistence;
- never load all day shards into one Python object;
- query only the requested date/range;
- stream rows where possible;
- return bounded projections;
- use database indexes for date/source/status/hash;
- keep raw bytes outside the UI process;
- hard-fail/hold when required promoted artifacts are unavailable.

## 10. What remains preserved from legacy UI

`app.py` UI is a presentation contract.

The six-panel navigation and user-facing workflows remain intact. The implementation behind each button is replaced gradually with lightweight runtime calls.

The UI must not know how crawling, sharding, hashing, quorum or heavy audit computation is implemented.

## 11. Migration sequence

### M0 — Architecture lock

This document is read before implementation. No runtime refactor is allowed to violate it.

### M1 — Separate Brain repository

Create/attach the existing `PROJECT_BRAIN_AI-main` project as its own GitHub repository. Do not duplicate Brain source into `xsmb-quant`.

### M2 — Raw artifact store

Complete PostgreSQL immutable raw artifact persistence.

### M3 — DAY_SHARD_V1

Implement deterministic per-day shard creation with FULL_27 as canonical truth and TAIL_27 as derived view.

### M4 — Manifest tree

Implement month/year/root manifests and Merkle-style hashes.

### M5 — AUDIT_PROJECTION_V1

Precompute fast UI-facing audit projections.

### M6 — Runtime adapter

Replace full-dataset runtime loading with indexed PostgreSQL queries against shards/projections.

### M7 — UI cutover

Keep `app.py` UI unchanged while replacing data/audit callbacks with runtime adapters.

### M8 — Brain evidence corridor

Export compact evidence envelopes to Brain through the registered corridor and capability gate.

### M9 — Historical backfill

Run 4,172+ historical data through bounded Build Plane batches. Missing dates remain UNKNOWN_GAP until independently evidenced. Holidays/Tet/COVID/non-draw states remain calendar evidence, never inferred from absence alone.

### M10 — Promotion

Only after runtime evidence, integrity evidence, lineage and governance gates pass.

## 12. Critical anti-patterns explicitly rejected

```text
Crawl -> load all -> backtest -> save manifest -> UI
```

and:

```text
Crawl -> Brain receives entire DB -> Brain computes everything -> UI
```

Both are rejected.

Correct:

```text
Crawl
  -> immutable raw artifact
  -> bounded DAY_SHARDs
  -> indexed canonical DB
  -> incremental audit projections
  -> compact evidence envelopes
       |                         |
       v                         v
   Render UI                Brain Governance
```

## 13. Completion invariant

The foundation is complete only when:

```text
FULL_27 canonical truth preserved
AND
raw provenance immutable
AND
shards deterministic
AND
hash tree verified
AND
audit projection fast
AND
Render runtime bounded
AND
Brain governance isolated
AND
all cross-room paths registered
AND
promotion remains fail-closed until evidence passes
```

This architecture is an extension of the existing V7 Build Plane contract, not a competing architecture.
