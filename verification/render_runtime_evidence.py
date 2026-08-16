"""Persist only compact execution evidence; never persist bulk payloads here."""
from __future__ import annotations

import hashlib
import json
import os
import resource
import time
from pathlib import Path

HARD_LIMIT_MB = 512
GUARD_MB = 320


def rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def write_evidence(path: Path, *, action_id: str, fixture: Path, status: str,
                   child_exit_code: int, elapsed_seconds: float,
                   stdout: str = "", stderr: str = "") -> dict:
    fixture_sha = hashlib.sha256(fixture.read_bytes()).hexdigest()
    evidence = {
        "evidence_version": "XSMB-RENDER-RUNTIME-V1",
        "action_id": action_id,
        "workload": "ONE_BOUNDED_FIXTURE",
        "fixture": str(fixture),
        "fixture_sha256": fixture_sha,
        "observed_peak_rss_mb": round(rss_mb(), 3),
        "memory_guard_mb": GUARD_MB,
        "platform_hard_limit_mb": HARD_LIMIT_MB,
        "elapsed_seconds": round(elapsed_seconds, 6),
        "child_exit_code": child_exit_code,
        "status": status if rss_mb() < GUARD_MB else "DENY_MEMORY_GUARD",
        "promotion": "DENY",
        "stdout_tail_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
        "stderr_tail_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
        "created_at_epoch": time.time(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return evidence
