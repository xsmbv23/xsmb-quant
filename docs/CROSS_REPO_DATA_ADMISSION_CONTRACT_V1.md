# Cross-Repository Data Admission Contract V1

## Authority

This contract defines the boundary between the XSMB data plane and Layer 1 Quant Engine.

```text
xsmb-quant = SOURCE TRUTH
Quant_Engine = CALCULATION / RESEARCH
Project_Brain_AI = GOVERNANCE / FORENSIC ADMISSION
```

## Canonical direction

```text
RAW SOURCE
  -> CANDIDATE FULL_27
  -> strict validation
  -> calendar admission
  -> independent-source quorum
  -> canonical FULL_27
  -> immutable canonical envelope
  -> Quant_Engine
```

No reverse edge exists.

## Required canonical envelope

A promoted envelope must carry at minimum:

- canonical schema/version
- draw date
- exactly 27 integer values in domain 0..99
- source evidence identifiers
- raw artifact SHA-256 references
- calendar state
- quorum/admission evidence
- canonical payload SHA-256
- immutable version identity

TAIL_27 may be included only as a derived field. It cannot be used to reconstruct FULL_27.

## Temporal law

Quant Engine must resolve T-1/T-2/T-7 by calendar date, not by array position.

Missing calendar dates must remain explicit. No synthetic fill is permitted.

## Admission law

```text
IMPLEMENTED != VERIFIED != PROMOTED
```

No canonical envelope may be consumed by research as truth merely because a file exists.

## Memory law

The Brain runtime must not hold the historical dataset. Historical work is bounded, streamed, or sharded. Render Free 512 MB remains a hard boundary with a conservative 320 MiB guard.

## Forensic law

A correction never mutates an existing canonical envelope. It creates a new version and new hash.
