# QUANT-N064 — Bounded Real-Source Observation / Parser Gate

## Work performed

The acquisition layer was advanced without opening canonical promotion.

### Code

- `data/ingestion/ketqua16_source_d.py` added.
- `data/ingestion/forensic_crawler_v2.py` made registry-driven.
- `ketqua16` and `xsmb` adapters wired into the main crawler.
- `tests/test_ketqua16_source_d.py` added.
- `tests/test_source_registry_acquisition.py` strengthened to require adapter declarations.
- `tests/test_real_receipt_20260809.py` added as a bounded parser fixture based on independently observed public source output.
- `data/ingestion/raw_artifact_store.py` now marks local capture as `LOCAL_EPHEMERAL` and `promotion_eligible=false`.
- `README.md` and `docs/AI_PROGRESS_LEDGER_V1.md` corrected for five-source registry and explicit durability semantics.

## External real-source observation

For 2026-08-09, public observations from `ketqua16.net` and `xsmb.com.vn` independently show the same FULL_27 sequence:

```text
12221 33704 95134 17327 04217 82286 56322 52512
96314 32250 4316 0742 8961 8299 3379 6567
7893 5442 1310 1473 468 841 949 21 77 29 97
```

A compact non-canonical observation receipt is stored at:

`evidence/external/QUANT-N064_20260809_real_source_observation.json`

## Critical distinction

This proves **public-source agreement and parser target shape**.

It does NOT prove:

- the Render crawler captured the bytes;
- the Render crawler produced the same raw SHA;
- durable evidence was written;
- a database read-after-write succeeded;
- canonical promotion is allowed.

Therefore:

```text
PUBLIC OBSERVATION        = PASS
FULL27 SHAPE              = PASS
SOURCE AGREEMENT          = OBSERVED
RENDER RUNTIME RECEIPT    = NOT_PROVEN
DURABLE EVIDENCE          = NOT_PROVEN
PROMOTION                 = DENY
```

## OOM policy

The new ketqua16 adapter uses streaming capture with an 8 MiB parse window and 64 KiB network chunks. It does not load multi-day history into memory. The crawler remains bounded by worker count.

## Next action

`QUANT-N065` — runtime execution proof: invoke the real acquisition path in a bounded execution context and capture non-secret source/day/raw-SHA/parser receipts. Do not promote. If the Render Free runtime cannot safely perform the probe, move the probe to an isolated execution room rather than increasing the Brain or web-service memory footprint.
