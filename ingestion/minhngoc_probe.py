from __future__ import annotations

import json
import os

from .minhngoc_adapter import fetch_raw, parse_full_27


def run_probe() -> dict[str, object]:
    capture = fetch_raw()
    candidate = parse_full_27(capture)
    result = {
        "status": "RUNTIME_VERIFIED",
        "promotion": "DENY",
        "source_id": candidate.source_id,
        "source_url": candidate.source_url,
        "retrieved_at": capture.retrieved_at,
        "http_status": capture.http_status,
        "content_type": capture.content_type,
        "raw_byte_length": capture.byte_length,
        "raw_sha256": capture.content_sha256,
        "draw_date": candidate.draw_date,
        "full_27_count": len(candidate.full_27),
        "full_27": list(candidate.full_27),
        "parser_version": candidate.parser_version,
        "content_hygiene": candidate.content_hygiene,
        "persistence": "EPHEMERAL_CAPTURE_ONLY",
        "promotable": False,
    }
    return result


if __name__ == "__main__":
    if os.environ.get("RUN_MINHNGOC_PROBE") != "1":
        raise SystemExit("RUN_MINHNGOC_PROBE must be 1")
    print(json.dumps({"event": "MINHNGOC_L0_PROBE", **run_probe()}, ensure_ascii=False, sort_keys=True), flush=True)
