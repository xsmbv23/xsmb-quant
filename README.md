# XSMB Quant — Data Foundation

The project is rebuilt from the data plane upward, with Project_Brain governance present from the foundation boundary.

## Locked truth model

- **FULL_27 is canonical source truth.**
- `DB/G1/G2/G3/G4/G5/G6/G7 = 1/1/2/6/4/6/3/4 = 27 prize values`.
- Prize widths are strict by group: `5/5/5/5/4/4/3/2` digits.
- `TAIL_27` is derived only: the last two digits of each FULL_27 value.
- `Ket_Qua_Loto27.xlsx` is legacy tail-only reference data, never forensic source truth.
- Missing source data is never inferred as a non-draw day.

## Legacy measurement already performed

The retained legacy workbook contains **4,172 data rows**, from `2015-01-01` through `2026-08-12`, with exactly 27 two-digit tails per row. It has **70 calendar gaps** in that span. These gaps remain `UNKNOWN_GAP` until authoritative calendar evidence is attached. A long gap exists from `2020-04-01` through `2020-04-22`; this is tracked as a COVID-era exception candidate, not silently hard-coded as a non-draw fact.

## Source roles

The source registry contains four independent candidates:

```text
PRIMARY TARGET      = ketqua16.net
IDENTITY / QUORUM B = xsmb.com.vn
OTHER INDEPENDENT   = minhngoc
OTHER INDEPENDENT   = xoso / xskt candidates as registered
```

A source's role does not make it canonical by itself. **No single website is allowed to promote its own output to source truth.** The default canonical quorum remains two independent sources, with conflicts and unresolved provenance causing DENY.

Advertisements, banners, navigation, scripts, analytics, sponsored blocks and other non-result content are explicitly **non-truth content**. Content hygiene may isolate them for parsing safety, but must never mutate the raw forensic bytes.

## Pipeline

```text
source HTML
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

## UI contract

The complete legacy `app.py` interface is preserved as a byte-level source contract. The backend/core will be replaced behind the UI; the presentation layer is not redesigned.

## Runtime rule

Render is currently foundation-only. It must not crawl, rebuild history, invent calendar states, or promote data. Current promotion state is **DENY**.

`IMPLEMENTED != VERIFIED != PROMOTED`.
