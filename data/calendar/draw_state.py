from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class DrawState(str, Enum):
    DRAW_EXPECTED = "DRAW_EXPECTED"
    DRAW_CONFIRMED = "DRAW_CONFIRMED"
    NON_DRAW_DAY = "NON_DRAW_DAY"
    UNKNOWN_GAP = "UNKNOWN_GAP"


@dataclass(frozen=True)
class CalendarDecision:
    day: date
    state: DrawState
    reason: str
    evidence_id: str | None = None


def missing_data_decision(day: date) -> CalendarDecision:
    """Never convert missing source data into a fabricated non-draw state."""
    return CalendarDecision(day, DrawState.UNKNOWN_GAP, "NO_AUTHORITATIVE_DRAW_EVIDENCE")


def confirmed_draw_decision(day: date, evidence_id: str) -> CalendarDecision:
    return CalendarDecision(day, DrawState.DRAW_CONFIRMED, "VALID_FULL_27_EVIDENCE", evidence_id)


def official_non_draw_decision(day: date, evidence_id: str) -> CalendarDecision:
    return CalendarDecision(day, DrawState.NON_DRAW_DAY, "OFFICIAL_NON_DRAW_EVIDENCE", evidence_id)
