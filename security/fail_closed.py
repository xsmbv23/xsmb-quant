from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FailClosedDecision:
    status: str
    promotion: str
    action: str
    reason: str


def terminal_halt(reason: str) -> FailClosedDecision:
    """Privileged security failure has no recovery-by-default path."""
    return FailClosedDecision(
        status="TERMINAL_HALT",
        promotion="DENY",
        action="HALT",
        reason=reason,
    )


def deny(reason: str) -> FailClosedDecision:
    return FailClosedDecision(
        status="DENY",
        promotion="DENY",
        action="HOLD",
        reason=reason,
    )
