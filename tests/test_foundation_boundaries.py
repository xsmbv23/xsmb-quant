from datetime import date

from brain.governance.policy import PromotionState, evaluate_foundation
from data.calendar.draw_state import DrawState, missing_data_decision
from data.ingestion.backfill_plan_v1 import BackfillAction, build_backfill_plan
from data.reconciliation.legacy_tail_reconciler import derive_tail27, reconcile


def test_missing_data_never_becomes_non_draw():
    decision = missing_data_decision(date(2020, 4, 10))
    assert decision.state == DrawState.UNKNOWN_GAP


def test_tail_is_derived_from_full_values():
    full = ["12345"] * 27
    assert derive_tail27(full) == ("45",) * 27


def test_legacy_mismatch_is_not_promoted():
    full = ["12345"] * 27
    legacy = ["99"] * 27
    result = reconcile(date(2020, 1, 1), legacy, full)
    assert result.status == "MISMATCH"


def test_unknown_gap_is_held():
    plan = build_backfill_plan(date(2020, 4, 10), date(2020, 4, 10), {})
    assert plan[0].action == BackfillAction.HOLD_UNKNOWN


def test_governance_denies_failed_gate():
    decision = evaluate_foundation(
        full27_valid=True,
        calendar_confirmed=True,
        provenance_valid=True,
        quorum_ok=False,
        conflict_free=True,
    )
    assert decision.promotion == PromotionState.DENY
