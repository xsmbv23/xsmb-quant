from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os

from security.selftest import run_security_selftest


SELFTEST_RESULT = run_security_selftest()
print(json.dumps({"event": "SECURITY_SELFTEST", **SELFTEST_RESULT}, sort_keys=True), flush=True)

SOURCE_PROBE_RESULT = None
if os.environ.get("RUN_MINHNGOC_PROBE") == "1":
    from ingestion.minhngoc_probe import run_probe
    SOURCE_PROBE_RESULT = run_probe()
    print(json.dumps({"event": "MINHNGOC_L0_PROBE", **SOURCE_PROBE_RESULT}, ensure_ascii=False, sort_keys=True), flush=True)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/health", "/verification/security", "/verification/source/minhngoc"):
            self.send_response(404)
            self.end_headers()
            return
        payload = {
            "project": "XSMB_FORENSIC",
            "component": "DATA_FOUNDATION",
            "status": "IMPLEMENTED_NOT_PROMOTED",
            "promotion": "DENY",
            "canonical_truth": "FULL_27",
            "derived_view": "TAIL_27",
            "runtime_mode": "FOUNDATION_ONLY",
            "security_verification": SELFTEST_RESULT,
            "minhngoc_probe": SOURCE_PROBE_RESULT,
        }
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
