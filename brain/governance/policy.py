from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PromotionState(str, Enum):
    DENY = "DENY"
    ALLOW = "ALLOW"


@dataclass(frozen=True)
class GovernanceDecision:
    promotion: PromotionState
    reasons: tuple[str, ...]
    policy_version: str = "PROJECT_BRAIN_GOVERNANCE_V1"


def evaluate_foundation(*, full27_valid: bool, calendar_confirmed: bool,
                        provenance_valid: bool, quorum_ok: bool,
                        conflict_free: bool) -> GovernanceDecision:
    failures: list[str] = []
    if not full27_valid:
        failures.append("FULL_27_INVALID")
    if not calendar_confirmed:
        failures.append("CALENDAR_NOT_CONFIRMED")
    if not provenance_valid:
        failures.append("PROVENANCE_INVALID")
    if not quorum_ok:
        failures.append("QUORUM_NOT_MET")
    if not conflict_free:
        failures.append("SOURCE_CONFLICT")

    if failures:
        return GovernanceDecision(PromotionState.DENY, tuple(failures))
    return GovernanceDecision(PromotionState.ALLOW, ())
