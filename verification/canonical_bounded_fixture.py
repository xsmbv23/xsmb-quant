"""Deterministic bounded XSMB fixture verifier.

This verifier deliberately processes one bounded source artifact only. It never
loads historical XSMB history into memory and it never promotes evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_LENGTHS = [5] * 10 + [4] * 10 + [3] * 3 + [2] * 4


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def independent_quorum(fixture: dict) -> tuple[bool, list[str]]:
    """Require explicit, distinct source identities; count alone is insufficient."""
    raw_ids = fixture.get("source_identities", [])
    if not isinstance(raw_ids, list):
        return False, []
    ids = [str(value).strip() for value in raw_ids if str(value).strip()]
    unique_ids = list(dict.fromkeys(ids))
    required = 2
    return len(unique_ids) >= required, unique_ids


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    prizes = fixture["source_prizes"]
    lengths = [len(str(x)) for x in prizes]

    full27_valid = len(prizes) == 27 and lengths == EXPECTED_LENGTHS
    tails = [int(str(x)[-2:]) for x in prizes]
    tail27_valid = tails == fixture["tails27"]

    source_sha = None
    source_sha_match = None
    if args.source:
        source_sha = sha256_bytes(args.source.read_bytes())
        source_sha_match = source_sha == fixture["source_file_sha256"]

    quorum_ok, source_identities = independent_quorum(fixture)
    canonical = "ALLOW" if full27_valid and tail27_valid and source_sha_match is not False and quorum_ok else "DENY"

    evidence = {
        "evidence_version": "XSMB-RUNTIME-EVIDENCE-V1",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "fixture_id": fixture["fixture_id"],
        "fixture_status": fixture["fixture_status"],
        "source_sha256_declared": fixture["source_file_sha256"],
        "source_sha256_observed": source_sha,
        "source_sha256_match": source_sha_match,
        "observed_date": fixture["source_row_date"],
        "full27_count": len(prizes),
        "semantic_lengths": lengths,
        "full27_valid": full27_valid,
        "tail27_count": len(tails),
        "tail27_derived_from_full27": tail27_valid,
        "quorum": {
            "source_count_declared": fixture.get("source_count"),
            "source_identities": source_identities,
            "distinct_source_count": len(source_identities),
            "required": 2,
            "status": "PASS" if quorum_ok else "FAIL",
            "reason": None if quorum_ok else "INDEPENDENT_SOURCE_IDENTITY_EVIDENCE_REQUIRED",
        },
        "canonical": canonical,
        "promotion": "DENY",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if canonical == "ALLOW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
