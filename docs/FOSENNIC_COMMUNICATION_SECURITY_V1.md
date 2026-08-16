# FOSENNIC COMMUNICATION SECURITY V1

## 1. Core idea

Every cross-subsystem communication is a **corridor crossing**.

A subsystem is a **room**. A layer is a **floor**. A message/request/capability is not allowed to move directly from room A to room B merely because Python can import/call it.

Required path:

```text
ROOM A
  |
  v
CORRIDOR GATE
  |
  +-- identity check
  +-- layer check
  +-- state check
  +-- capability check (when privileged)
  +-- schema/type check
  +-- provenance/lineage check
  +-- authorization check
  +-- anti-replay / freshness check when applicable
  |
  v
ROOM B
```

A failed gate means `DENY` or `TERMINAL_HALT` depending on privilege/state. Never silently fall through.

## 2. Floors / layers

### L0 — Physical / Raw Data

Sources, raw bytes, raw HTML, raw Excel artifacts, immutable hashes.

Authority: source evidence only.

Can provide: raw evidence.

Cannot receive: Quant decisions, Brain commands, promotion decisions.

### L1 — Data Foundation

Parser, calendar, FULL_27 validator, provenance, reconciliation, canonical data store.

Can consume: L0 evidence.

Can produce: validated canonical data + evidence.

Cannot mutate L0.

### L2 — Temporal / Research Data

TemporalSnapshot, feature construction, historical/OOS split, research datasets.

Can consume: validated L1 data.

Can produce: snapshot/features/research artifacts.

Cannot repair source truth.

### L3 — Quant / Decision

Alpha sensors, regime, scoring, probability, sizing, strategy decisions.

Can consume: L2 snapshots and approved policy manifests.

Can produce: candidate decisions.

Cannot bypass L4 safeguards or L5 governance.

### L4 — Risk / Safety / Execution Boundary

Lookahead shield, data quality shield, liquidity, risk budget, stress, correlation, circuit breakers, execution feasibility.

Can consume: L3 candidate decisions + L2 lineage.

Can produce: ALLOW / REDUCE / SKIP / DENY candidate execution.

Cannot manufacture alpha/data.

### L5 — Governance / Brain / Capability Authority

Project_Brain_AI, invariant evaluation, state machine, capability authority, promotion gate.

Can consume: signed/hashed evidence and stateful subsystem outputs.

Can produce: DENY / HOLD / CANDIDATE / explicit capability issuance when all prerequisites are satisfied.

Cannot rewrite source truth.

### L6 — Presentation / External Communication

app.py UI, reports, Telegram/alerts/API presentation.

Can consume: sanitized authorized read models.

Cannot query raw secrets or mutate canonical truth.

## 3. Directionality

Default allowed flow is downward for data and upward for evidence/governance:

```text
L0 -> L1 -> L2 -> L3 -> L4 -> L5

L5 -> L6  (authorized read/report only)
L4 -> L6  (execution/report status only)
L2 -> L6  (authorized historical read model only)

Feedback:
L5 -> L1/L2/L3 only through versioned policy/evidence contracts.
Never direct mutable calls.
```

The UI is not a governance authority.

## 4. Corridor types

Every cross-room call must declare a corridor class:

- `DATA_READ`
- `DATA_WRITE`
- `EVIDENCE_WRITE`
- `POLICY_READ`
- `POLICY_PROPOSE`
- `GOVERNANCE_REQUEST`
- `CAPABILITY_REQUEST`
- `CAPABILITY_CONSUME`
- `REPORT_READ`
- `EXTERNAL_ALERT`

Default deny for unknown corridor classes.

## 5. Message envelope

Every privileged cross-room message should carry a logical envelope:

```text
message_id
correlation_id
source_room
source_layer
source_identity
source_state
source_artifact_sha
payload_schema
payload_version
requested_corridor
requested_capability
issued_at
expires_at (when applicable)
nonce (when applicable)
policy_manifest_sha
```

Do not put secrets into evidence logs.

## 6. Corridor gate sequence

```text
1. Resolve source identity
2. Resolve source layer
3. Resolve destination room/layer
4. Check direction policy
5. Check message schema/version
6. Check artifact/data lineage
7. Check current runtime state
8. Check capability requirement
9. Check authorization/policy manifest
10. Check freshness / nonce / replay condition
11. Execute call
12. Verify returned identity/lineage
13. Record audit event
```

A privileged corridor is **two-way verified**: sender proves authority and receiver verifies the envelope; receiver output is then checked before being accepted by sender.

## 7. Capability security

Existing forensic architecture already establishes CapabilityAuthority as the single source of truth and requires explicit capability for holdout materialization. It also requires monotonic state transitions and absorbing `TERMINAL_HALT`. This communication model generalizes that pattern to every privileged corridor.

Rules:

- capabilities are opaque, scoped and short-lived where possible;
- no capability is inferred from a boolean flag;
- capability issuance requires state + policy + evidence prerequisites;
- capability consumption is one-shot when the operation is one-shot;
- capability must be cleared/revoked on failure;
- a capability cannot cross into a lower-trust layer without an explicit adapter;
- `TERMINAL_HALT` always means no capability.

## 8. Upper vs lower layer rule

### Upper layer

Governance, Brain, policy, authorization, promotion.

Upper layers may **constrain** lower layers.

They must not invent lower-layer facts.

### Lower layer

Raw data, ingestion, canonical store, temporal data, computation.

Lower layers may provide evidence/results upward.

They must not self-promote or self-authorize.

### Forbidden privilege inversion

```text
L0 crawler -> direct Brain command       FORBIDDEN
L0 crawler -> direct promotion           FORBIDDEN
L3 Quant -> direct source repair         FORBIDDEN
L6 UI -> raw DB mutation                 FORBIDDEN
L6 UI -> capability issuance             FORBIDDEN
Brain -> raw source rewrite              FORBIDDEN
Render environment -> governance truth  FORBIDDEN
```

## 9. Security boundaries inherited from forensic core

Preserve and generalize these established invariants:

- `CapabilityAuthority` is the single source of truth for privileged lifecycle state.
- All post-init state changes pass through the transition primitive.
- `TERMINAL_HALT` is absorbing.
- Pre/post boundaries use single snapshots to detect cross-scope mismatch.
- Exact descriptor/object identity must be preserved across privileged lifecycle stages.
- Cleanup failures are not swallowed.
- Outer orchestration failures force fail-closed.
- Artifact identity is hash-bound before execution.

These principles are evidenced by the prior V18 forensic governance architecture and must not be weakened when the new data system is connected.

## 10. Anti-TOCTOU / identity continuity

For any privileged operation:

```text
DESCRIPTOR CREATED
      |
      v
HASH / IDENTITY SNAPSHOT
      |
      v
AUTHORIZATION
      |
      v
CONSUME EXACT SAME INSTANCE
      |
      v
POST-CONSUMPTION IDENTITY CHECK
      |
      v
COMMIT STATE TRANSITION
```

Never re-query an object and assume it is the same object.

## 11. Communication audit

Every corridor crossing must produce an append-only audit event containing at minimum:

```text
communication_id
source_room
source_layer
destination_room
destination_layer
corridor_type
message_schema
source_state
decision
reason_code
source_artifact_sha
policy_manifest_sha
timestamp
```

Do not log credentials, DATABASE_URL, tokens or capability secrets.

## 12. Security state machine

```text
UNAUTHENTICATED
  -> AUTHENTICATED
  -> AUTHORIZED
  -> CAPABILITY_ISSUED (only if required)
  -> CONSUMED
  -> REVOKED/CLEARED
```

Invalid transition:

```text
-> DENY
```

Security exception during privileged lifecycle:

```text
-> TERMINAL_HALT
```

## 13. Future Bot requirement

Before modifying any subsystem, the Bot must answer from repository artifacts:

1. What room am I in?
2. What layer am I in?
3. What room/layer am I communicating with?
4. Which corridor class is being crossed?
5. What evidence authorizes the crossing?
6. Is a capability required?
7. What state transition occurs?
8. What audit event is emitted?
9. What is the fail-closed destination if the gate fails?
10. Does this create a forbidden privilege inversion?

If any answer is unknown, the Bot must not invent it. It must mark the path `UNKNOWN` and keep promotion `DENY`.

## 14. Relationship to Data Foundation

The crawler is not allowed to call Quant directly.

```text
Crawler L0
   ↓ DATA_READ/EVIDENCE_WRITE corridor
Data Foundation L1
   ↓ DATA_READ corridor
Temporal L2
   ↓ DATA_READ corridor
Quant L3
   ↓ GOVERNANCE_REQUEST corridor
Risk L4
   ↓ GOVERNANCE_REQUEST corridor
Brain L5
   ↓ REPORT_READ corridor
app.py / external reporting L6
```

The same corridor model applies to database access, Render services, GitHub automation, Brain calls and future external APIs.

## 15. Completion condition

The Fosennic communication layer is complete only when:

- every cross-room dependency is listed;
- every room has a layer/trust classification;
- every corridor has an allow/deny rule;
- every privileged corridor has authorization/capability rules;
- every privileged operation has pre/post identity checks;
- every failure path terminates safely;
- every crossing is auditable without leaking secrets;
- future Bots can reconstruct the communication graph from repository artifacts alone.

Until then:

`COMMUNICATION SECURITY = INCOMPLETE`

`PROMOTION = DENY`
