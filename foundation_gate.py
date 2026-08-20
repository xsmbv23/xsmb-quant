from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import subprocess
import sys
from pathlib import Path

from security.selftest import run_security_selftest

SELFTEST_RESULT = run_security_selftest()
print(json.dumps({"event": "SECURITY_SELFTEST", **SELFTEST_RESULT}, sort_keys=True), flush=True)

BOUNDED_FIXTURE_RESULT = None
if os.environ.get("RUN_BOUNDED_FIXTURE") == "1":
    fixture = Path("fixtures/2026-08-12/full27_fixture.json")
    output = Path("evidence/runtime/2026-08-12/render_bounded.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "verification/render_safe_runner.py", str(fixture), "--output", str(output)]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    BOUNDED_FIXTURE_RESULT = {
        "status": "RUNTIME_VERIFIED" if proc.returncode in (0, 2) else "DENY",
        "promotion": "DENY",
        "fixture": str(fixture),
        "runner_exit_code": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
    }
    print(json.dumps({"event": "BOUNDED_FIXTURE_RUNTIME", **BOUNDED_FIXTURE_RESULT}, ensure_ascii=False, sort_keys=True), flush=True)

SOURCE_PROBE_RESULT = None
if os.environ.get("RUN_MINHNGOC_PROBE") == "1":
    from ingestion.minhngoc_probe import run_probe
    SOURCE_PROBE_RESULT = run_probe()
    print(json.dumps({"event": "MINHNGOC_L0_PROBE", **SOURCE_PROBE_RESULT}, ensure_ascii=False, sort_keys=True), flush=True)

REAL_SOURCE_QUORUM_RESULT = None
if os.environ.get("RUN_REAL_SOURCE_QUORUM_PROBE") == "1":
    try:
        from verification.real_source_quorum_probe import run_probe
        REAL_SOURCE_QUORUM_RESULT = run_probe()
    except Exception as exc:
        REAL_SOURCE_QUORUM_RESULT = {"status": "DENY", "promotion": "DENY", "reason": type(exc).__name__ + ":" + str(exc)[:240]}
    print(json.dumps({"event": "REAL_SOURCE_QUORUM_PROBE", **REAL_SOURCE_QUORUM_RESULT}, ensure_ascii=False, sort_keys=True), flush=True)

PERSISTENCE_RESULT = {"status": "PENDING", "promotion": "DENY", "reason": "RUN_DB_PERSISTENCE_NOT_ENABLED"}
if os.environ.get("RUN_DB_PERSISTENCE") == "1":
    try:
        from ingestion.minhngoc_adapter import fetch_raw, parse_full_27
        from storage.raw_artifacts import persist_raw_artifact
        capture = fetch_raw()
        candidate = parse_full_27(capture)
        persisted = persist_raw_artifact(capture, candidate.parser_version)
        PERSISTENCE_RESULT = {
            "status": "RUNTIME_VERIFIED",
            "promotion": "DENY",
            "source_id": capture.source_id,
            "raw_sha256": capture.content_sha256,
            "raw_byte_length": capture.byte_length,
            "draw_date": candidate.draw_date,
            "full_27_count": len(candidate.full_27),
            "raw_artifact_id": persisted.raw_artifact_id,
            "inserted": persisted.inserted,
            "persistence": "POSTGRESQL_TLS_REQUIRED",
        }
    except Exception as exc:
        PERSISTENCE_RESULT = {"status": "DENY", "promotion": "DENY", "reason": type(exc).__name__ + ":" + str(exc)[:240]}
    print(json.dumps({"event": "RAW_ARTIFACT_PERSISTENCE", **PERSISTENCE_RESULT}, ensure_ascii=False, sort_keys=True), flush=True)

DURABILITY_RESULT = {"status": "PENDING", "promotion": "DENY", "database_url_present": bool(os.environ.get("DATABASE_URL"))}
if os.environ.get("RUN_EVIDENCE_ROUNDTRIP") == "1":
    try:
        from verification.durable_evidence_roundtrip import run_roundtrip
        DURABILITY_RESULT = run_roundtrip()
    except Exception as exc:
        DURABILITY_RESULT = {"status": "DENY", "promotion": "DENY", "reason": type(exc).__name__ + ":" + str(exc)[:240]}
    print(json.dumps({"event": "EVIDENCE_DURABILITY_ROUNDTRIP", **DURABILITY_RESULT}, ensure_ascii=False, sort_keys=True), flush=True)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/health", "/verification/security", "/verification/source/minhngoc", "/verification/bounded", "/verification/durability", "/verification/source/quorum"):
            self.send_response(404); self.end_headers(); return
        payload = {
            "project": "XSMB_FORENSIC", "component": "DATA_FOUNDATION", "status": "IMPLEMENTED_NOT_PROMOTED",
            "promotion": "DENY", "canonical_truth": "FULL_27", "derived_view": "TAIL_27", "runtime_mode": "FOUNDATION_ONLY",
            "security_verification": SELFTEST_RESULT, "bounded_fixture": BOUNDED_FIXTURE_RESULT,
            "minhngoc_probe": SOURCE_PROBE_RESULT, "real_source_quorum_probe": REAL_SOURCE_QUORUM_RESULT,
            "raw_artifact_persistence": PERSISTENCE_RESULT, "evidence_durability": DURABILITY_RESULT,
        }
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_HEAD(self):
        self.send_response(200 if self.path in ("/", "/health", "/verification/security", "/verification/source/minhngoc", "/verification/bounded", "/verification/durability", "/verification/source/quorum") else 404)
        self.send_header("Content-Length", "0"); self.end_headers()

    def log_message(self, *_args):
        return


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
