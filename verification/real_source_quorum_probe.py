"""Bounded two-source historical acquisition probe.

This is candidate-evidence generation only. It fetches one date from each
registered primary source sequentially, keeps the evidence objects separate,
and never promotes truth. Quorum is delegated to the canonical reconciliation
gate so source registration, independence, observation integrity, conflict
handling, and quorum semantics cannot drift between the probe and admission.
"""
from __future__ import annotations

import hashlib
import json
import resource
from datetime import date
from pathlib import Path

from data.ingestion.ketqua16_source_d import fetch_source_d
from data.ingestion.xsmb_source_b import fetch_source_b
from data.reconciliation.reconciliation_gate_v1 import SourceObservation, reconcile

TARGET_DATE = date.fromisoformat("2026-08-12")
OUTPUT = Path("evidence/runtime/2026-08-12/real_source_quorum.json")


def _source_evidence(record):
    return {
        "source_id": record.source_id,
        "source_url": record.source_url,
        "observed_date": record.draw_date,
        "raw_sha256": record.source_html_sha256,
        "parse_block_sha256": record.parse_block_sha256,
        "full27_count": len(record.full_prizes),
        "full27_fingerprint": hashlib.sha256(
            "|".join(record.full_prizes).encode("utf-8")
        ).hexdigest(),
        "full27": list(record.full_prizes),
        "status": "OBSERVED",
    }


def run_probe() -> dict:
    evidence = {
        "evidence_version": "XSMB-REAL-SOURCE-PROBE-V2",
        "target_date": TARGET_DATE.isoformat(),
        "promotion": "DENY",
        "canonical_truth": "FULL_27",
        "sources": [],
        "quorum": {"required": 2, "distinct_source_count": 0, "status": "DENY"},
        "result_match": False,
        "status": "DENY",
    }

    records = []
    errors = []
    for fetcher in (fetch_source_d, fetch_source_b):
        try:
            records.append(fetcher(TARGET_DATE))
        except Exception as exc:
            errors.append({"source": fetcher.__name__, "error": f"{type(exc).__name__}:{str(exc)[:240]}"})

    evidence["sources"] = [_source_evidence(record) for record in records]
    evidence["errors"] = errors

    observations = [
        SourceObservation(record.source_id, tuple(record.full_prizes), record.source_html_sha256)
        for record in records
    ]
    decision = reconcile(observations, minimum_independent_sources=2)
    evidence["admission"] = {
        "state": decision.state,
        "reasons": list(decision.reasons),
        "evidence_sha256": decision.evidence_sha256,
    }

    distinct_ids = list(dict.fromkeys(item["source_id"] for item in evidence["sources"]))
    evidence["quorum"] = {
        "required": 2,
        "distinct_source_count": len(distinct_ids),
        "source_identities": distinct_ids,
        "status": "PASS" if decision.state == "CANONICAL_CANDIDATE" else "DENY",
    }

    if len(records) == 2 and len(distinct_ids) == 2 and not errors:
        evidence["result_match"] = records[0].full_prizes == records[1].full_prizes

    if decision.state == "CANONICAL_CANDIDATE" and evidence["result_match"]:
        evidence["status"] = "CANDIDATE"
    elif decision.state == "DENY" and "SOURCE_CONFLICT" in decision.reasons:
        evidence["status"] = "DENY_CONFLICT"
    else:
        evidence["status"] = "DENY"

    evidence["memory_peak_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return evidence


if __name__ == "__main__":
    print(json.dumps(run_probe(), ensure_ascii=False, indent=2))
