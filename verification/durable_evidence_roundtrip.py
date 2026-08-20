"""Verify durable evidence without loading bulk source data.

Requires DATABASE_URL at runtime. Missing/unusable DB is DENY, never PASS.
The runtime entrypoint only verifies an already-produced compact evidence envelope;
it never manufactures one during verification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from verification.durable_evidence_sink import persist_envelope, read_envelope


def canonical(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def evidence_sha(value: dict) -> str:
    body = dict(value)
    body.pop("evidence_sha256", None)
    return hashlib.sha256(canonical(body)).hexdigest()


def verify_envelope(path: Path) -> tuple[int, dict]:
    env = json.loads(path.read_text(encoding="utf-8"))
    expected = env.get("evidence_sha256")
    if not expected:
        return 3, {"status": "DENY", "promotion": "DENY", "reason": "EVIDENCE_SHA_MISSING"}

    computed = evidence_sha(env)
    if computed != expected:
        return 3, {"status": "DENY", "promotion": "DENY", "reason": "EVIDENCE_SHA_LOCAL_MISMATCH"}

    try:
        persist_envelope(env)
        recovered = read_envelope(expected)
    except Exception as exc:
        return 4, {
            "status": "DENY",
            "promotion": "DENY",
            "reason": "DURABILITY_UNAVAILABLE",
            "error_type": type(exc).__name__,
        }

    recovered_sha_field = recovered.get("evidence_sha256")
    recovered_sha_computed = evidence_sha(recovered)
    status = (
        "PASS"
        if recovered_sha_field == expected and recovered_sha_computed == expected
        else "DENY_READBACK_HASH_MISMATCH"
    )
    return (0 if status == "PASS" else 5), {
        "status": status,
        "promotion": "DENY",
        "evidence_sha256": expected,
        "readback_sha256": recovered_sha_computed,
        "readback_sha_field": recovered_sha_field,
    }


def run_roundtrip() -> dict:
    """Foundation-gate adapter; requires an externally produced envelope path."""
    path_value = os.environ.get("EVIDENCE_ENVELOPE_PATH", "").strip()
    if not path_value:
        return {"status": "DENY", "promotion": "DENY", "reason": "EVIDENCE_ENVELOPE_PATH_MISSING"}
    path = Path(path_value)
    if not path.is_file():
        return {
            "status": "DENY",
            "promotion": "DENY",
            "reason": "EVIDENCE_ENVELOPE_NOT_FOUND",
            "path": str(path),
        }
    _, result = verify_envelope(path)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("envelope", type=Path)
    args = ap.parse_args()
    code, result = verify_envelope(args.envelope)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
