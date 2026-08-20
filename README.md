# XSMB Quant — Data Foundation

The project is rebuilt from the data plane upward, with Project_Brain governance present from the foundation boundary.

## Locked truth model

- **FULL_27 is canonical source truth.**
- `DB/G1/G2/G3/G4/G5/G6/G7 = 1/1/2/6/4/6/3/4 = 27 prize values`.
- Prize widths are strict by group: `5/5/5/5/4/4/3/2` digits.
- `TAIL_27` is derived only: the last two digits of each FULL_27 value.
- `Ket_Qua_Loto27.xlsx` is legacy tail-only reference data, never forensic source truth.
- Missing source data is never inferred as a non-draw day.

## Source registry and acquisition invariant

The authoritative registry currently contains **five** independent candidates:

```text
publisher_a = minhngoc
publisher_b = xoso
publisher_c = xskt
publisher_d = ketqua16
publisher_e = xsmb
```

The registry is the source of acquisition truth. The crawler may not silently maintain a separate source list. Every registered source must have an acquisition route and every unregistered source is rejected.

The primary real-source pair for the current research gate is:

```text
SOURCE A = ketqua16.net
SOURCE B = xsmb.com.vn
```

A source's role does not make it canonical by itself. **No single website is allowed to promote its own output to source truth.** The default canonical quorum remains two independent sources, with conflicts and unresolved provenance causing DENY.

Advertisements, banners, navigation, scripts, analytics, sponsored blocks and other non-result content are explicitly **non-truth content**. Content hygiene may isolate them for parsing safety, but must never mutate the raw forensic bytes.

## Pipeline

```text
SOURCE REGISTRY
  -> acquisition adapter
  -> raw HTML SHA256
  -> content hygiene (ads/scripts/navigation isolated; raw bytes preserved)
  -> strict FULL_27 extraction
  -> source/day fingerprint
  -> calendar state
  -> independent-source quorum
  -> conflict ledger
  -> Brain governance
  -> candidate canonical FULL_27
  -> derived TAIL_27
```

### Acquisition adapters

```text
minhngoc -> generic date URL adapter
xoso     -> generic date URL adapter
xskt     -> generic date URL adapter
ketqua16 -> ketqua16_source_d.py
xsmb     -> xsmb_source_b.py
```

`ketqua16_source_d.py` and `xsmb_source_b.py` use bounded streaming capture and parse only the target date block. The crawler does not treat advertisements, scripts or navigation as source truth.

## Admission invariant

Source truth and Forensic admission are related but not interchangeable.

```text
SOURCE EXISTS
    -> SOURCE BINDING / ORIGIN
    -> RESULT TRANSPORT
    -> OFFICIAL RESULT PANEL
    -> CANDIDATE
    -> EXCEL_VS_WEB MATCH
    -> CANONICAL QUORUM
    -> TRUTH ADMISSION
```

Each gate owns its own evidence. `PASS` is local and only a prerequisite for the next gate. There is **no PASS inheritance** and `UNKNOWN` is never converted to PASS by inference.

## Raw evidence durability

`runtime/raw` is a **write-once local capture cache**, not a durable forensic evidence store. Raw bytes are SHA-256 bound and never overwritten, but local Render filesystem persistence must not be treated as durable evidence. Durable promotion requires an explicit durable sink and a successful write → read → SHA-256 match.

## UI contract

The complete legacy `app.py` interface is preserved as a byte-level source contract. The backend/core will be replaced behind the UI; the presentation layer is not redesigned.

## Runtime rule

Render is currently foundation-only. It must not crawl, rebuild history, invent calendar states, or promote data. Current promotion state is **DENY**.

`IMPLEMENTED != VERIFIED != EVIDENCE_BOUND != PROMOTED`.
