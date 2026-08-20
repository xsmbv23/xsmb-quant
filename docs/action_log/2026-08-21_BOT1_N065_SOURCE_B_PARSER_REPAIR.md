# BOT1 N065 — SOURCE B PARSER REPAIR

## Scope
Track B / `xsmb-quant` only. Brain Runtime Track A is not modified.

## Evidence that triggered repair
Render runtime for commit `f25bb8cc1282d5c2e16dafc98cdc7d7fb81f1622` completed the bounded real-source quorum probe for `2026-08-12` with:

- `ketqua16` parsed successfully: 27 values, raw SHA and parse-block SHA present.
- `xsmb` failed with `ValueError:prize group names/order mismatch`.
- quorum remained DENY with one distinct source identity.
- promotion remained DENY.
- runtime memory peak reported `127120 KiB` (~124 MiB), below the 320 MiB guard.

## Root cause
`xsmb_source_b.py` collected groups under source labels (`ĐB`, `G1`...`G7`) and passed that dictionary directly to `validate_prize_groups()`, whose canonical contract requires insertion order `DB`, `G1`...`G7`. The equivalent source-D adapter already normalizes source-specific labels into canonical names before validation.

## Repair
Commit `647972b60f2f4874aa474a3870cd6b2dc8a9af5f` normalizes Source B groups into the canonical ordered envelope before validation.

## Admission status
IMPLEMENTED = YES
RUNTIME_VERIFIED = PENDING
QUORUM = DENY until both independent sources parse and agree
CANONICAL PROMOTION = DENY

## Next autonomous action
After deployment, inspect Render runtime evidence. If Source B parses, verify exact result equality and independent-source quorum. If quorum still fails, diagnose the next concrete source/data blocker rather than promoting or bypassing the gate.
