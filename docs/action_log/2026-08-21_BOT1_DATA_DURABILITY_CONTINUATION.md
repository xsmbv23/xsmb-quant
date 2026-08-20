# Bot 1 — Data Durability Continuation

Date: 2026-08-21
Repository: `xsmbv23/xsmb-quant`
Role: SOURCE TRUTH / DATA PLANE

## Policy basis

Core mission: REAL DATA → VALID RESEARCH → VALID BACKTEST → EDGE → EV/P&L/ROI → ROBUSTNESS/RISK/DRIFT → CONTROLLED ACTION.

Forensic is the admission/control mechanism, not the destination. PASS is local; PASS is prerequisite-only; no PASS inheritance; UNKNOWN is not PASS; default-deny; own-gate evidence is required.

## Continuation finding

The previous durability verifier checked the database row's `evidence_sha256` field against the expected hash. That alone was insufficient: a persisted JSON envelope could theoretically have its contents altered while retaining the hash field. Readback verification therefore must recompute the canonical SHA from the recovered envelope itself.

## Repair 1 — readback integrity

Updated `verification/durable_evidence_roundtrip.py` to:

1. Compute the source envelope hash through one canonical helper.
2. Verify the supplied envelope against its declared `evidence_sha256`.
3. Persist and read back the envelope.
4. Recompute the SHA from the recovered JSON body.
5. Require BOTH the recovered hash field and the recomputed recovered hash to equal the original expected SHA.
6. Return DENY on any mismatch; never promote.

Commit: `f14eb522e0275c82e46bd5e5aacfab9c9eecbae2`

## Repair 2 — executable regression coverage

Added `tests/test_durable_evidence_roundtrip.py` covering:

- valid envelope + matching readback → PASS locally;
- readback payload tampering while retaining the hash field → DENY;
- local envelope hash mismatch → DENY before persistence.

Commit: `5cb70763d4525c15c6dd28d06367debefd7cf224`

Added `.github/workflows/durable-evidence-tests.yml` so the durability integrity tests execute on pushes to `main`, pull requests, and manual dispatch.

Commit: `85c4f5419f728c2b08f0957e6941d71149946f82`

## Verification status

IMPLEMENTED = YES
CI EXECUTION RECEIPT = NOT YET PROVEN
RENDER DURABILITY = NOT YET PROVEN
PROMOTION = DENY

The GitHub connector currently reports no workflow run associated with the repair commit and no combined status checks. Therefore no PASS is inferred from the existence of the workflow file or test code.

## Next action

Obtain an exact-current CI execution receipt for the durability tests. If CI passes, move to the confirmed DATA Render workspace and execute an exact-current bounded durability test with a real externally produced compact evidence envelope and real `DATABASE_URL`. Verify:

- original envelope SHA;
- recovered envelope SHA recomputation;
- recovered JSON identity;
- repeated persistence/idempotency;
- no promotion side effect;
- memory remains within the repository's Render guard.

Do not infer source quorum, FULL_27 admission, backtest validity, EV/P&L, or action permission from durability alone.

## Parallel-work boundary

Bot 1 remains scoped to `xsmbv23/xsmb-quant`. No `Project_Brain_AI` or `Quant_Engine` mutation is performed by this workstream.
