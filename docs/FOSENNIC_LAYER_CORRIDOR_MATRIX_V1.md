# FOSENNIC LAYER / CORRIDOR MATRIX V1

| Room | Layer | Trust | Allowed inputs | Allowed outputs | Forbidden |
|---|---|---|---|---|---|
| Raw Sources | L0 | evidence | external bytes | raw artifact | policy/Quant mutation |
| Data Foundation | L1 | validated | L0 | FULL_27, provenance, evidence | raw rewrite |
| Temporal/Research | L2 | derived | L1 | snapshots/features/research | future leakage |
| Quant | L3 | analytical | L2 + frozen policy | candidate decision | source repair/promotion |
| Risk/Safety | L4 | protective | L3 + L2 lineage | allow/reduce/skip/deny | alpha invention |
| Brain/Governance | L5 | authority | evidence + state | deny/hold/candidate/capability | source invention |
| Presentation | L6 | untrusted output | authorized read models | UI/report/alert | raw mutation/capability |

## Corridor policy

| Corridor | Direction | Privilege | Required gates |
|---|---|---|---|
| DATA_READ | lower→upper | low | identity + schema + lineage |
| DATA_WRITE | upper→lower | high | state + authorization + lineage + audit |
| EVIDENCE_WRITE | lower→upper | medium | provenance + immutable append + audit |
| POLICY_READ | upper→lower | medium | manifest identity + version |
| POLICY_PROPOSE | lower→upper | medium | candidate version + evidence |
| GOVERNANCE_REQUEST | L3/L4→L5 | high | envelope + state + evidence |
| CAPABILITY_REQUEST | L5→privileged room | critical | state + authorization + capability issuance |
| CAPABILITY_CONSUME | privileged→privileged | critical | exact capability identity + one-shot rules + post-check |
| REPORT_READ | core→L6 | low | sanitized read model |
| EXTERNAL_ALERT | L5/L4→external | high | sanitized payload + destination allowlist + audit |

## Mandatory envelope

`message_id, correlation_id, source_room, source_layer, source_identity, source_state, payload_schema, payload_version, corridor_type, source_artifact_sha, policy_manifest_sha, issued_at, expires_at, nonce`

## Default policy

**Default DENY.** Every new room or corridor must be explicitly registered. Imports/calls alone do not constitute authorization.
