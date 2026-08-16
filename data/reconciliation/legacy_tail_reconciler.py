from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Sequence


@dataclass(frozen=True)
class ReconciliationResult:
    date: date
    legacy_tail27: tuple[str, ...]
    derived_tail27: tuple[str, ...]
    status: str
    reason: str


def derive_tail27(full_prizes: Sequence[str]) -> tuple[str, ...]:
    """Derive 27 two-digit tails without changing canonical FULL_27."""
    if len(full_prizes) != 27:
        raise ValueError(f"FULL_27 requires 27 values, got {len(full_prizes)}")
    return tuple(value[-2:] for value in full_prizes)


def reconcile(date_value: date, legacy_tail27: Iterable[str], full_prizes: Sequence[str]) -> ReconciliationResult:
    legacy = tuple(legacy_tail27)
    if len(legacy) != 27:
        return ReconciliationResult(date_value, legacy, (), "INVALID_LEGACY", "legacy row is not exactly 27 tails")
    derived = derive_tail27(full_prizes)
    if legacy == derived:
        return ReconciliationResult(date_value, legacy, derived, "MATCH", "legacy tail equals derived FULL_27 tail")
    return ReconciliationResult(date_value, legacy, derived, "MISMATCH", "legacy tail differs from derived FULL_27")


# This module deliberately does not promote or mutate canonical data.
