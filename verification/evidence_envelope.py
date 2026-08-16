"""Deterministic, compact evidence envelope.

The envelope contains hashes and bounded runtime metadata only. It deliberately
never accepts the raw source payload or a historical dataset.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

FORBIDDEN_KEYS = {
    "raw_payload", "workbook", "historical_rows", "historical_dataframe",
    "all_results", "source_bytes", "full_history"
}


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def build_envelope(*, action_id: str, source_sha256: str, fixture_sha256: str,
                   full27_sha256: str, tail27_sha256: str, manifest_sha256: str,
                   status: str, promotion: str, resource_status: str,
                   peak_rss_mb: float, elapsed_seconds: float) -> dict[str, Any]:
    envelope = {
        "evidence_version": "XSMB-EVIDENCE-ENVELOPE-V1",
        "action_id": action_id,
        "source_sha256": source_sha256,
        "fixture_sha256": fixture_sha256,
        "full27_sha256": full27_sha256,
        "tail27_sha256": tail27_sha256,
        "manifest_sha256": manifest_sha256,
        "status": status,
        "promotion": promotion,
        "resource_status": resource_status,
        "peak_rss_mb": round(float(peak_rss_mb), 3),
        "elapsed_seconds": round(float(elapsed_seconds), 6),
    }
    if FORBIDDEN_KEYS.intersection(envelope):
        raise ValueError("bulk payload key entered evidence envelope")
    envelope["evidence_sha256"] = hashlib.sha256(canonical_json(envelope)).hexdigest()
    return envelope
