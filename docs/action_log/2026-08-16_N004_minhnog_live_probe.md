# N004 — First bounded source adapter / Minh Ngoc live probe

**Actor:** GPT-5.6 Luna

## Result

`RUNTIME_VERIFIED` for the L0→L1 adapter execution path.

Exactly one registered source was used: `minhngoc`. The adapter captured the raw HTTP response first, hashed the raw bytes, then parsed a candidate FULL_27. Content hygiene statistics were captured separately. No source adapter was connected to promotion or to any other source.

## Runtime evidence

- Service: `srv-da0obdpt0dsc73a5ubbg`
- Source: `minhngoc`
- URL: `https://www.minhngoc.net.vn/xo-so-mien-bac.html`
- Retrieval: `2026-08-16T11:31:24.258919+00:00`
- HTTP status: `200`
- Raw bytes: `196596`
- Raw SHA-256: `3213bf273337f1716b7269e7d9a3c332c763bf8fce24bd1e1dfd0b4549be0672`
- Draw date extracted: `15/08/2026`
- FULL_27 count: `27`
- Parser: `MINHNGOC_XSMB_FULL27_V1`
- Evidence: `evidence/runtime/N004_minhnog_live_probe_v1.json`
- Evidence SHA-256: `853d56af9f2cb7cea0299b3aa58170a25a536d94b9acf65b5ea8efe2e90536aa`

## Content hygiene

The raw page contained navigation/ads/scripts/forms. They were not treated as canonical data. Observed counts:

- script tags: 24
- style tags: 5
- link tags: 3
- form tags: 5
- table tags: 29

## Important boundary

The raw capture is currently `EPHEMERAL_CAPTURE_ONLY`. The bytes were captured and hashed in the Render runtime but are not yet persisted in an immutable database evidence store. Therefore this action does **not** promote the source artifact.

`PROMOTION = DENY`.

## Next action

N005 — establish immutable raw-artifact persistence in `xsmb_runtime_db` with TLS-required database connectivity, then bind the N004 raw SHA and provenance record to the database without changing the raw bytes.
