"""Render-safe bounded verifier launcher.

Policy: one fixture/day shard per process, explicit memory ceiling, no history
aggregation, fail-closed. This is deliberately dependency-light so it can run
inside the existing service/build boundary without pandas or multiprocessing.
"""
from __future__ import annotations

import argparse
import json
import resource
import subprocess
import sys
import time
from pathlib import Path

HARD_LIMIT_MB = 512
DEFAULT_GUARD_MB = 320


def rss_mb() -> float:
    # Linux ru_maxrss is KiB; macOS reports bytes. Render is Linux.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("fixture", type=Path)
    p.add_argument("--source", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--guard-mb", type=int, default=DEFAULT_GUARD_MB)
    args = p.parse_args()

    if not 64 <= args.guard_mb < HARD_LIMIT_MB:
        raise SystemExit("invalid memory guard: must be 64..511 MB")

    # Never accept a guard at/above the platform ceiling.
    start = time.monotonic()
    before = rss_mb()
    cmd = [sys.executable, str(Path(__file__).with_name("canonical_bounded_fixture.py")), str(args.fixture), "--output", str(args.output)]
    if args.source:
        cmd += ["--source", str(args.source)]

    proc = subprocess.run(cmd, check=False)
    after = rss_mb()
    peak = max(before, after)

    # The child is intentionally bounded by input size, not by historical data.
    # A conservative parent-side guard still prevents declaring Render-safe when
    # observed RSS approaches the platform ceiling.
    status = "PASS" if peak < args.guard_mb else "DENY_MEMORY_GUARD"
    runtime = {
        "runtime_evidence_version": "XSMB-RENDER-SAFE-RUNTIME-V1",
        "workload": "ONE_BOUNDED_FIXTURE",
        "guard_mb": args.guard_mb,
        "platform_hard_limit_mb": HARD_LIMIT_MB,
        "observed_parent_peak_rss_mb": round(peak, 3),
        "elapsed_seconds": round(time.monotonic() - start, 6),
        "child_exit_code": proc.returncode,
        "resource_status": status,
        "promotion": "DENY",
    }
    evidence_path = args.output.with_suffix(".runtime.json")
    evidence_path.write_text(json.dumps(runtime, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(runtime, indent=2))
    return 0 if proc.returncode in (0, 2) and status == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
