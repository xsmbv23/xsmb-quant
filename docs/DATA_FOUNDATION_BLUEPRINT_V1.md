# XSMB FORENSIC DATA FOUNDATION — BLUEPRINT V1

> This document is the canonical handoff for any future AI/Bot. Read this before modifying the data layer.
>
> **Core doctrine:** DATA FIRST. `IMPLEMENTED != VERIFIED != PROMOTED`. No synthetic data. No silent repair. No look-ahead. No mutation of canonical truth from UI, Quant, or AI.

## 1. Mission

Rebuild the XSMB historical and live data foundation from source evidence while preserving forensic lineage. The legacy Excel `Ket_Qua_Loto27.xlsx` is a reconciliation reference, not the canonical source of full prize values.

Canonical truth is `FULL_27`; `TAIL_27` is derived from it.

## 2. Canonical prize topology

```text
DRAW DATE
  |
  +-- DB  : 1 x 5 digits
  +-- G1  : 1 x 5 digits
  +-- G2  : 2 x 5 digits
  +-- G3  : 6 x 5 digits
  +-- G4  : 4 x 4 digits
  +-- G5  : 6 x 4 digits
  +-- G6  : 3 x 3 digits
  +-- G7  : 4 x 2 digits
  |
  +-- TOTAL = 27 prize values
  |
  +-- TAIL_27 = derived last-two-digit projection
```

Never reverse the direction. `TAIL_27 -> FULL_27` is forbidden because information has been discarded.

## 3. End-to-end data flow

```text
                 +----------------------+
                 | Source Registry V2   |
                 | minhngoc             |
                 | xoso                 |
                 | xskt                 |
                 | ketqua16             |
                 +----------+-----------+
                            |
                            v
                 +----------------------+
                 | HTTP / raw acquisition|
                 +----------+-----------+
                            |
                            v
                 +----------------------+
                 | RAW BYTE ARTIFACT     |
                 | URL + timestamp + SHA |
                 +----------+-----------+
                            |
                            v
                 +----------------------+
                 | Content Hygiene       |
                 | AD/SCRIPT/NAV isolate |
                 +----------+-----------+
                            |
                            v
                 +----------------------+
                 | Source-specific       |
                 | parser -> CANDIDATE   |
                 +----------+-----------+
                            |
                            v
                 +----------------------+
                 | ONE strict FULL_27    |
                 | validator             |
                 +----------+-----------+
                            |
             +--------------+--------------+
             |                             |
             v                             v
      calendar gate                 source identity
             |                             |
             +--------------+--------------+
                            v
                 +----------------------+
                 | Cross-source quorum  |
                 | >=2 independent      |
                 +----------+-----------+
                            |
                   +--------+--------+
                   |                 |
                conflict           agree
                   |                 |
                   v                 v
                 DENY          Brain Governance
                                     |
                              +------+------+
                              |             |
                            DENY          evidence
                                            |
                                            v
                                      CANDIDATE ONLY
                                            |
                                      Promotion DENY
```

## 4. Calendar state machine

Every date must have one explicit state:

```text
DRAW_EXPECTED
   |
   +-- valid source evidence --> DRAW_CONFIRMED
   |
   +-- authoritative closure evidence --> NON_DRAW_DAY
   |
   +-- no authoritative evidence --> UNKNOWN_GAP
```

Rules:

- `missing data != NON_DRAW_DAY`.
- Weekday logic is never sufficient to declare a non-draw day.
- Tet/New Year and COVID suspension/resumption are explicit historical evidence cases.
- `UNKNOWN_GAP` blocks canonical promotion.

## 5. Source/content boundary

Ads are not data.

```text
RAW HTML
 |
 +-- SCRIPT / STYLE / NOSCRIPT -> IGNORE FOR EXTRACTION
 +-- AD / BANNER / ADS PROVIDER -> IGNORE FOR EXTRACTION
 +-- NAVIGATION -> IGNORE FOR EXTRACTION
 +-- UNKNOWN -> CANDIDATE, never canonical
 +-- DATA TABLE -> CANDIDATE, then strict FULL_27 validation
```

The Brain never edits the website. It governs whether a parsed candidate can proceed.

RAW is retained unchanged for forensic review.

## 6. Source-specific parser rule

Each site may have a different HTML structure. Therefore:

```text
SOURCE A parser --+
SOURCE B parser --+
SOURCE C parser --+--> common CandidateRecord --> FULL_27 validator
SOURCE D parser --+
```

Do not create four competing canonical schemas.

`CandidateRecord` must contain at minimum:

- draw date
- source id
- source URL
- retrieval timestamp
- raw artifact SHA256
- parsed prize groups
- parser version
- table/content fingerprint

## 7. Reconciliation rule

Legacy Excel flow:

```text
Ket_Qua_Loto27.xlsx
       |
       v
 legacy TAIL_27
       |
       |  reference only
       v
FULL_27 from independent source
       |
       v
 derive TAIL_27
       |
       v
 compare
```

Outcomes:

```text
MATCH       -> reconciliation PASS
MISMATCH    -> CONFLICT / DENY
MISSING     -> UNKNOWN / DENY
```

Never reconstruct missing FULL values from tail values.

## 8. Quorum

Default canonical quorum:

```text
minimum independent sources = 2
```

One source can produce evidence but cannot alone promote canonical history.

Conflicting sources are retained in a conflict ledger. Do not silently choose the prettier/newer/more convenient page.

## 9. Brain governance

Project_Brain_AI is a governance layer from the foundation onward.

```text
OBSERVE
  |
VALIDATE
  |
ENFORCE POLICY
  |
+-----> DENY
|
+-----> candidate evidence
```

The Brain cannot:

- invent numbers;
- infer missing draws;
- overwrite canonical records;
- repair conflicting sources silently;
- bypass validation;
- promote unsupported evidence;
- mutate production truth.

## 10. Evidence hierarchy

```text
RAW SOURCE BYTES
      > parsed candidate
      > validated FULL_27
      > derived TAIL_27
      > Quant features
      > AI interpretation
```

Higher-level layers cannot rewrite lower-level truth.

## 11. Runtime separation

Render is an execution boundary, not the source of truth.

```text
GitHub = code/contracts/versioned governance
Render = runtime/execution
Postgres = persistent canonical storage when promoted
Raw artifact store = immutable provenance
```

Render startup must never silently crawl or manufacture historical records.

## 12. UI preservation

Legacy `app.py` is a presentation contract. Preserve its complete user-facing interface. Replace the core behind it.

```text
OLD UI
  |
  +---- unchanged presentation boundary
  |
NEW data/core/Quant/Brain
```

Do not redesign UI while rebuilding the data foundation.

## 13. Historical reconstruction

The legacy workbook currently represents a historical reference window with gaps. The reconstruction runner must be calendar-aware and source-evidence driven.

For every requested date:

```text
calendar state?
  |
  +-- NON_DRAW_DAY -> record closure evidence; no fake draw
  |
  +-- UNKNOWN_GAP -> HOLD; do not guess
  |
  +-- DRAW_EXPECTED -> fetch sources
                           |
                           +-- quorum pass -> candidate FULL_27
                           +-- quorum fail -> DENY
```

Do not assume a fixed number of historical rows is the target. Target = calendar-complete, evidence-backed draw history.

## 14. Promotion state machine

```text
RAW
 |
v
PARSED CANDIDATE
 |
v
VALIDATED FULL_27
 |
v
CALENDAR VERIFIED
 |
v
PROVENANCE VERIFIED
 |
v
QUORUM VERIFIED
 |
v
BRAIN POLICY
 |
+---- fail ----> DENY
 |
 pass
 |
v
CANDIDATE EVIDENCE
 |
 |
 +---- separate future gate ----> PROMOTION
```

No current foundation component should directly call promotion.

## 15. Future AI handoff checklist

Before touching code, a new Bot must verify:

- [ ] Read this blueprint.
- [ ] Read `docs/FOUNDATION_DECISIONS_V1.md`.
- [ ] Read `data/contracts/full27_v1.json`.
- [ ] Read `data/contracts/calendar_v1.md`.
- [ ] Read `brain/governance/PROJECT_BRAIN_GOVERNANCE_V1.md`.
- [ ] Read `data/ingestion/source_registry_v2.json`.
- [ ] Treat Excel as reconciliation reference only.
- [ ] Preserve raw provenance.
- [ ] Never infer non-draw from absence.
- [ ] Never derive FULL_27 from TAIL_27.
- [ ] Never silently resolve source conflicts.
- [ ] Never allow AI to mutate source truth.
- [ ] Never mark runtime execution as verified without execution evidence.
- [ ] Keep promotion DENY until every required gate is evidenced.

## 16. Completion criterion for the DATA FOUNDATION layer

The foundation is complete only when all are true:

1. Source adapters for all registered sources exist and are tested.
2. Raw artifacts have deterministic provenance and retention rules.
3. Content hygiene isolates advertising/scripts/navigation without changing raw evidence.
4. FULL_27 validation is strict and universal.
5. Calendar ledger covers historical expected/non-draw/unknown states with evidence.
6. Historical backfill can execute reproducibly from a clean environment.
7. Legacy Excel reconciliation is automated and reports every mismatch/gap.
8. Quorum/conflict ledger is automated.
9. Brain governance is enforced before canonical promotion.
10. Persistent canonical schema and indexes are defined.
11. Evidence records are immutable/read-only and reproducible.
12. UI preservation boundary is documented.
13. Render runtime does not manufacture truth.
14. A new AI can read the blueprint and continue without changing architecture accidentally.

Until all 14 are satisfied:

`DATA FOUNDATION = INCOMPLETE`

and:

`PROMOTION = DENY`.
