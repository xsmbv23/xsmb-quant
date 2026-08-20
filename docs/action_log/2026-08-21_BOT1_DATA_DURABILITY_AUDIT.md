# Bot 1 — Data Durability Audit

Date: 2026-08-21
Repository: `xsmbv23/xsmb-quant`
Role: SOURCE TRUTH / DATA PLANE

## Policy basis

Core mission remains:

REAL DATA → VALID RESEARCH → VALID BACKTEST → EDGE → EV/P&L/ROI → ROBUSTNESS/RISK/DRIFT → CONTROLLED ACTION.

Forensic is an admission/control mechanism, not the destination. PASS is local, PASS is prerequisite-only, there is no PASS inheritance, UNKNOWN is not PASS, default-deny applies, and each gate requires its own evidence.

## Audit finding

The repository already had raw-artifact persistence with a unique `(source_id, content_sha256)` identity and TLS-required PostgreSQL. The persistence path returned an artifact ID but did not expose a direct readback operation for proving that the stored bytes still match the capture hash.

A second integration defect was found in `foundation_gate.py`: the `RUN_EVIDENCE_ROUNDTRIP=1` path imported `run_roundtrip`, while `verification/durable_evidence_roundtrip.py` exposed only `main()`. The configured runtime verification path therefore could not execute its intended adapter and would fall closed.

## Safe repairs performed

1. Added `storage.raw_artifacts.read_raw_artifact()` to read back the persisted source artifact by immutable artifact ID.
2. Added `verification/raw_artifact_roundtrip.py` to verify source identity, byte length, and SHA-256 after database readback. It never promotes; failure is DENY.
3. Added `run_roundtrip()` to `verification/durable_evidence_roundtrip.py`, requiring an explicitly supplied `EVIDENCE_ENVELOPE_PATH`. The verifier does not manufacture evidence during verification.

Commits:

- `87a4bcbdf69ddb6309aa0ca4bceb8200cd2eb251`
- `3cf99ad4798a213301d7843a718779e04b7c1853`
- `8c3e92dcc777946f1ec1ed1d9d2e9123a37022b8`

## Verification status

IMPLEMENTED = YES

LOCAL/CI EXECUTION RECEIPT = NOT YET PROVEN

RENDER RUNTIME VERIFICATION = BLOCKED pending confirmed Render workspace selection in the current tool session.

PROMOTION = DENY

## Next action

1. Verify the new commits through repository CI/runtime execution.
2. On the confirmed Render DATA workspace, verify the exact-current `xsmb-quant` deployment and run the bounded raw-artifact durability roundtrip with real `DATABASE_URL`.
3. Confirm readback SHA, byte length, source identity, and idempotent repeat behavior from runtime evidence.
4. Only then consider the durability gate locally PASS; do not infer source quorum, canonical FULL_27 admission, backtest validity, EV, P&L, or action permission from this gate.

## Boundary

Bot 1 is operating on `xsmb-quant` only in this workstream. No mutation of Project_Brain_AI or Quant_Engine was performed by this action log.
