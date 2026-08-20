# QUANT-N063 — Proactive Acquisition Drift Repair

## Finding

The authoritative source registry contained five sources:

- minhngoc
- xoso
- xskt
- ketqua16
- xsmb

The previous `forensic_crawler_v2.py` maintained a separate three-source hardcoded map. This was an architecture drift: registry state and executable acquisition state could diverge silently.

## Repair

1. Main crawler now derives default source IDs from `source_registry_v2.json`.
2. Unregistered source IDs are rejected.
3. Existing `xsmb_source_b.py` is wired into the main acquisition path.
4. New `ketqua16_source_d.py` is wired into the main acquisition path.
5. Registry/acquisition parity tests were added.
6. `README.md` and `AI_PROGRESS_LEDGER_V1.md` were corrected from stale four-source language to the authoritative five-source registry.
7. Local raw metadata is explicitly marked `LOCAL_EPHEMERAL` and `promotion_eligible=false`.

## Forensic rule

```text
REGISTRY ENTRY
    !=
COLLECTOR PROOF

COLLECTOR PASS
    !=
CANONICAL TRUTH

GATE PASS
    !=
NEXT GATE PASS
```

Every gate owns its own evidence.

## Durable evidence boundary

`runtime/raw` remains a write-once local capture cache only. It is not durable forensic evidence. Durable promotion remains blocked until a durable sink is bound and a real write/read/hash-match is observed.

## Next action

`N064` — run static tests plus a bounded real-source probe for `ketqua16` and `xsmb` on a known historical date. Record compact non-secret receipts only; keep promotion DENY.
