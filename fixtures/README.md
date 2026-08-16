# Bounded XSMB Fixture

This directory contains only tiny deterministic verification fixtures.

## Purpose

Prove the data chain without loading historical XSMB data into Render/Brain RAM.

Required chain:

```text
raw source bytes
  -> SHA-256
  -> FULL_27 validation
  -> provenance/quorum decision
  -> TAIL_27 derivation
  -> one-day shard
  -> manifest
  -> compact evidence
```

The fixture is not production data and must never be promoted as production history.

## Rules

- No synthetic prize values presented as real-world observations.
- Fixture status must be explicit.
- Source identity and payload SHA must be deterministic.
- FULL_27 is authoritative; TAIL_27 is derived.
- No reverse reconstruction from TAIL_27.
- No full historical workbook loading.
