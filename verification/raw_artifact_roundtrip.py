"""Verify raw-artifact durability and identity after PostgreSQL persistence.

This is a bounded verification path: it captures one source artifact, persists it,
reads it back by the immutable (source_id, SHA-256) identity, and re-hashes the
stored bytes. Any unavailable or inconsistent evidence is DENY, never PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json

from ingestion.minhngoc_adapter import fetch_raw
from storage.raw_artifacts import persist_raw_artifact


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="minhngoc")
    args = ap.parse_args()

    if args.source != "minhngoc":
        print(json.dumps({"status": "DENY", "promotion": "DENY", "reason": "SOURCE_NOT_IMPLEMENTED"}))
        return 3

    try:
        capture = fetch_raw()
        persisted = persist_raw_artifact(capture, "runtime_roundtrip")
        from storage.raw_artifacts import read_raw_artifact
        recovered = read_raw_artifact(persisted.raw_artifact_id)
    except Exception as exc:
        print(json.dumps({
            "status": "DENY",
            "promotion": "DENY",
            "reason": "RAW_ARTIFACT_DURABILITY_UNAVAILABLE",
            "error_type": type(exc).__name__,
        }))
        return 4

    recovered_bytes = recovered["raw_bytes"]
    recovered_sha = hashlib.sha256(recovered_bytes).hexdigest()
    identity_ok = (
        recovered["source_id"] == capture.source_id
        and recovered["content_sha256"] == capture.content_sha256
        and recovered_sha == capture.content_sha256
        and recovered["byte_length"] == len(recovered_bytes) == capture.byte_length
    )
    status = "PASS" if identity_ok else "DENY_RAW_ARTIFACT_IDENTITY_MISMATCH"
    print(json.dumps({
        "status": status,
        "promotion": "DENY",
        "raw_artifact_id": persisted.raw_artifact_id,
        "source_id": recovered["source_id"],
        "content_sha256": recovered["content_sha256"],
        "readback_sha256": recovered_sha,
        "byte_length": recovered["byte_length"],
        "inserted": persisted.inserted,
    }, ensure_ascii=False, sort_keys=True))
    return 0 if status == "PASS" else 5


if __name__ == "__main__":
    raise SystemExit(main())
