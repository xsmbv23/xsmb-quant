from pathlib import Path
from data.reconciliation.legacy_reconcile import load_legacy
from data.calendar.calendar_ledger import build

P = Path(__file__).resolve().parents[1] / 'fixtures' / 'legacy' / 'Ket_Qua_Loto27.xlsx'


def test_legacy_shape():
    rows = load_legacy(P)
    assert len(rows) == 4172
    assert rows[0].day.isoformat() == '2015-01-01'
    assert rows[-1].day.isoformat() == '2026-08-12'
    assert all(len(r.tails) == 27 for r in rows)


def test_calendar_does_not_infer_non_draw():
    ledger = build(P)
    assert ledger['promotion'] == 'DENY'
    assert sum(x['state'] == 'UNKNOWN_GAP' for x in ledger['rows']) == 70
