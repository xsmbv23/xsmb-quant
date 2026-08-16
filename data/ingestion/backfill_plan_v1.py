from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum


class BackfillAction(str, Enum):
    FETCH = "FETCH"
    SKIP_NON_DRAW = "SKIP_NON_DRAW"
    HOLD_UNKNOWN = "HOLD_UNKNOWN"


@dataclass(frozen=True)
class BackfillDay:
    day: date
    action: BackfillAction
    reason: str


def build_backfill_plan(start: date, end: date, calendar_states: dict[date, str]) -> list[BackfillDay]:
    plan: list[BackfillDay] = []
    day = start
    while day <= end:
        state = calendar_states.get(day, "UNKNOWN_GAP")
        if state == "NON_DRAW_DAY":
            action = BackfillAction.SKIP_NON_DRAW
            reason = "authoritative non-draw calendar evidence"
        elif state == "DRAW_CONFIRMED":
            action = BackfillAction.FETCH
            reason = "confirmed draw requires source reconciliation"
        else:
            action = BackfillAction.HOLD_UNKNOWN
            reason = "unknown calendar state; no fabricated absence"
        plan.append(BackfillDay(day, action, reason))
        day += timedelta(days=1)
    return plan


# The planner never fetches, writes, or promotes. It only creates an auditable plan.
