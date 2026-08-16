"""Verify durable evidence without loading bulk source data.

Requires DATABASE_URL at runtime. Missing/unusable DB is DENY, never PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from verification.durable_evidence_sink import persist_envelope, read_envelope


def canonical(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("envelope", type=Path)
    args = ap.parse_args()

    env = json.loads(args.envelope.read_text(encoding="utf-8"))
    expected = env.get("evidence_sha256")
    if not expected:
        print(json.dumps({"status": "DENY", "reason": "EVIDENCE_SHA_MISSING"}))
        return 3

    # Recompute exactly the same identity used by evidence_envelope.py.
    body = dict(env)
    body.pop("evidence_sha256", None)
    computed = hashlib.sha256(canonical(body)).hexdigest()
    if computed != expected:
        print(json.dumps({"status": "DENY", "reason": "EVIDENCE_SHA_LOCAL_MISMATCH"}))
        return 3

    try:
        persist_envelope(env)
        recovered = read_envelope(expected)
    except Exception as exc:
        print(json.dumps({
            "status": "DENY",
            "reason": "DURABILITY_UNAVAILABLE",
            "error_type": type(exc).__name__,
        }))
        return 4

    recovered_sha = recovered.get("evidence_sha256")
    status = "PASS" if recovered_sha == expected else "DENY_READBACK_HASH_MISMATCH"
    print(json.dumps({
        "status": status,
        "evidence_sha256": expected,
        "readback_sha256": recovered_sha,
        "promotion": "DENY",
    }, ensure_ascii=False))
    return 0 if status == "PASS" else 5


if __name__ == "__main__":
    raise SystemExit(main())
