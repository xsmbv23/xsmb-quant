from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from data.ingestion.xsmb_source_b import fetch_source_b


def main() -> int:
    target = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date(2026, 8, 12)
    record = fetch_source_b(target)
    out = {
        "receipt_version": "SOURCE-B-FULL27-V1",
        "source_id": record.source_id,
        "source_url": record.source_url,
        "draw_date": record.draw_date,
        "source_html_sha256": record.source_html_sha256,
        "parse_block_sha256": record.parse_block_sha256,
        "full27": list(record.full_prizes),
        "full27_count": len(record.full_prizes),
        "tail27": list(record.tails27),
        "promotion": "DENY",
        "quorum": {"source_count": 1, "required": 2},
        "policy": "CANDIDATE_ONLY_UNTIL_INDEPENDENT_SOURCE_AGREEMENT",
    }
    Path("source_b_receipt.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
