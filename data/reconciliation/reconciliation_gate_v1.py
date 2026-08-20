from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


REGISTRY_PATH = Path(__file__).resolve().parents[1] / "ingestion" / "source_registry_v2.json"


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


def _independence_groups() -> dict[str, str]:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if payload.get("version") != "SOURCE_REGISTRY_V2":
        raise ValueError("SOURCE_REGISTRY_VERSION_UNSUPPORTED")
    groups: dict[str, str] = {}
    for source in payload.get("sources", []):
        source_id = source.get("id")
        independence_group = source.get("independence_group")
        if not source_id or not independence_group:
            raise ValueError("SOURCE_REGISTRY_INDEPENDENCE_GROUP_MISSING")
        groups[source_id] = independence_group
    return groups


def reconcile(observations: list[SourceObservation], minimum_independent_sources: int = 2) -> ReconciliationDecision:
    if minimum_independent_sources < 1:
        return ReconciliationDecision("DENY", None, sha256(b"INVALID_QUORUM").hexdigest(), ("INVALID_MINIMUM_INDEPENDENT_SOURCES",))
    if not observations:
        return ReconciliationDecision("DENY", None, sha256(b"EMPTY").hexdigest(), ("NO_SOURCE_OBSERVATIONS",))

    try:
        independence_groups = _independence_groups()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return ReconciliationDecision("DENY", None, sha256(b"REGISTRY_INVALID").hexdigest(), (f"SOURCE_REGISTRY_INVALID:{type(exc).__name__}",))

    unknown_sources = sorted({obs.source_id for obs in observations if obs.source_id not in independence_groups})
    if unknown_sources:
        evidence = "|".join(sorted(o.raw_sha256 for o in observations)).encode()
        return ReconciliationDecision("DENY", None, sha256(evidence).hexdigest(), (f"UNREGISTERED_SOURCE:{','.join(unknown_sources)}",))

    groups: dict[tuple[str, ...], list[SourceObservation]] = {}
    for obs in observations:
        groups.setdefault(obs.full27, []).append(obs)

    if len(groups) != 1:
        evidence = "|".join(sorted(o.raw_sha256 for o in observations)).encode()
        return ReconciliationDecision("DENY", None, sha256(evidence).hexdigest(), ("SOURCE_CONFLICT",))

    values, members = next(iter(groups.items()))
    independent = len({independence_groups[m.source_id] for m in members})
    evidence = "|".join(sorted(m.raw_sha256 for m in members)).encode()
    if independent < minimum_independent_sources:
        return ReconciliationDecision("DENY", None, sha256(evidence).hexdigest(), ("QUORUM_NOT_MET",))

    return ReconciliationDecision("CANONICAL_CANDIDATE", values, sha256(evidence).hexdigest(), ())
