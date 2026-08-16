from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class SourceObservation:
    source_id: str
    full27: tuple[str, ...]
    raw_sha256: str


@dataclass(frozen=True)
class ReconciliationDecision:
    state: str
    canonical_full27: tuple[str, ...] | None
    evidence_sha256: str
    reasons: tuple[str, ...]


def reconcile(observations: list[SourceObservation], minimum_independent_sources: int = 2) -> ReconciliationDecision:
    if not observations:
        return ReconciliationDecision("DENY", None, sha256(b"EMPTY").hexdigest(), ("NO_SOURCE_OBSERVATIONS",))

    groups: dict[tuple[str, ...], list[SourceObservation]] = {}
    for obs in observations:
        groups.setdefault(obs.full27, []).append(obs)

    if len(groups) != 1:
        evidence = "|".join(sorted(o.raw_sha256 for o in observations)).encode()
        return ReconciliationDecision("DENY", None, sha256(evidence).hexdigest(), ("SOURCE_CONFLICT",))

    values, members = next(iter(groups.items()))
    independent = len({m.source_id for m in members})
    evidence = "|".join(sorted(m.raw_sha256 for m in members)).encode()
    if independent < minimum_independent_sources:
        return ReconciliationDecision("DENY", None, sha256(evidence).hexdigest(), ("QUORUM_NOT_MET",))

    return ReconciliationDecision("CANONICAL_CANDIDATE", values, sha256(evidence).hexdigest(), ())
