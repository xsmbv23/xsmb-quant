from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
from pathlib import Path

from data.calendar.draw_state import DrawState
from data.ingestion.forensic_crawler_v2 import crawl, reconcile


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def main() -> int:
    parser = argparse.ArgumentParser(description='Forensic historical XSMB backfill; candidate-only.')
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True)
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--out', default='runtime/evidence/historical_backfill.json')
    args = parser.parse_args()

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    records, errors = crawl(daterange(start, end), workers=args.workers)
    consensus, conflicts = reconcile(records)

    result = {
        'protocol': 'HISTORICAL_INGESTION_V1',
        'range': {'start': args.start, 'end': args.end},
        'records_observed': len(records),
        'candidate_consensus': consensus,
        'conflicts': conflicts,
        'errors': errors,
        'promotion': 'DENY',
        'state': 'CANDIDATE_EVIDENCE_ONLY',
    }
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'records_observed': len(records), 'candidates': len(consensus), 'conflicts': len(conflicts), 'errors': len(errors), 'promotion': 'DENY'}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
