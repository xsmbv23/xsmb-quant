from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import secrets
from typing import Any, FrozenSet, Mapping


class Layer(str, Enum):
    L0_RAW = "L0_RAW"
    L1_DATA = "L1_DATA_FOUNDATION"
    L2_TEMPORAL = "L2_TEMPORAL_RESEARCH"
    L3_QUANT = "L3_QUANT_DECISION"
    L4_RISK = "L4_RISK_SAFETY"
    L5_GOVERNANCE = "L5_BRAIN_GOVERNANCE"
    L6_PRESENTATION = "L6_PRESENTATION"


class Corridor(str, Enum):
    DATA_READ = "DATA_READ"
    DATA_WRITE = "DATA_WRITE"
    EVIDENCE_WRITE = "EVIDENCE_WRITE"
    POLICY_READ = "POLICY_READ"
    POLICY_PROPOSE = "POLICY_PROPOSE"
    GOVERNANCE_REQUEST = "GOVERNANCE_REQUEST"
    CAPABILITY_REQUEST = "CAPABILITY_REQUEST"
    CAPABILITY_CONSUME = "CAPABILITY_CONSUME"
    REPORT_READ = "REPORT_READ"
    EXTERNAL_ALERT = "EXTERNAL_ALERT"


class DenyReason(str, Enum):
    UNKNOWN_CORRIDOR = "UNKNOWN_CORRIDOR"
    WRONG_DIRECTION = "WRONG_DIRECTION"
    LAYER_VIOLATION = "LAYER_VIOLATION"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    LINEAGE_MISSING = "LINEAGE_MISSING"
    STATE_INVALID = "STATE_INVALID"
    AUTHORIZATION_MISSING = "AUTHORIZATION_MISSING"
    CAPABILITY_MISSING = "CAPABILITY_MISSING"
    CAPABILITY_EXPIRED = "CAPABILITY_EXPIRED"
    REPLAY_DETECTED = "REPLAY_DETECTED"
    PROVENANCE_MISMATCH = "PROVENANCE_MISMATCH"


@dataclass(frozen=True)
class Room:
    name: str
    layer: Layer
    identity: str


@dataclass(frozen=True)
class MessageEnvelope:
    message_id: str
    correlation_id: str
    source_room: str
    source_layer: Layer
    source_identity: str
    source_state: str
    destination_room: str
    destination_layer: Layer
    corridor: Corridor
    payload_schema: str
    payload_version: str
    source_artifact_sha: str | None
    policy_manifest_sha: str | None
    issued_at: str
    expires_at: str | None
    nonce: str
    payload: Mapping[str, Any]

    @staticmethod
    def build(
        *,
        source: Room,
        destination: Room,
        corridor: Corridor,
        source_state: str,
        payload_schema: str,
        payload_version: str,
        payload: Mapping[str, Any],
        source_artifact_sha: str | None = None,
        policy_manifest_sha: str | None = None,
        expires_at: str | None = None,
    ) -> "MessageEnvelope":
        return MessageEnvelope(
            message_id=secrets.token_hex(16),
            correlation_id=secrets.token_hex(16),
            source_room=source.name,
            source_layer=source.layer,
            source_identity=source.identity,
            source_state=source_state,
            destination_room=destination.name,
            destination_layer=destination.layer,
            corridor=corridor,
            payload_schema=payload_schema,
            payload_version=payload_version,
            source_artifact_sha=source_artifact_sha,
            policy_manifest_sha=policy_manifest_sha,
            issued_at=datetime.now(timezone.utc).isoformat(),
            expires_at=expires_at,
            nonce=secrets.token_urlsafe(18),
            payload=dict(payload),
        )

    def canonical_digest(self) -> str:
        data = {
            "message_id": self.message_id,
            "correlation_id": self.correlation_id,
            "source_room": self.source_room,
            "source_layer": self.source_layer.value,
            "source_identity": self.source_identity,
            "source_state": self.source_state,
            "destination_room": self.destination_room,
            "destination_layer": self.destination_layer.value,
            "corridor": self.corridor.value,
            "payload_schema": self.payload_schema,
            "payload_version": self.payload_version,
            "source_artifact_sha": self.source_artifact_sha,
            "policy_manifest_sha": self.policy_manifest_sha,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "nonce": self.nonce,
            "payload": self.payload,
        }
        raw = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        return hashlib.sha256(raw).hexdigest()


# Explicit allow-list. Unknown room/layer/corridor combinations are denied.
_ALLOWED: FrozenSet[tuple[Layer, Layer, Corridor]] = frozenset({
    (Layer.L0_RAW, Layer.L1_DATA, Corridor.DATA_READ),
    (Layer.L0_RAW, Layer.L1_DATA, Corridor.EVIDENCE_WRITE),
    (Layer.L1_DATA, Layer.L2_TEMPORAL, Corridor.DATA_READ),
    (Layer.L1_DATA, Layer.L5_GOVERNANCE, Corridor.EVIDENCE_WRITE),
    (Layer.L2_TEMPORAL, Layer.L3_QUANT, Corridor.DATA_READ),
    (Layer.L2_TEMPORAL, Layer.L5_GOVERNANCE, Corridor.POLICY_PROPOSE),
    (Layer.L3_QUANT, Layer.L4_RISK, Corridor.GOVERNANCE_REQUEST),
    (Layer.L4_RISK, Layer.L5_GOVERNANCE, Corridor.GOVERNANCE_REQUEST),
    (Layer.L5_GOVERNANCE, Layer.L3_QUANT, Corridor.POLICY_READ),
    (Layer.L5_GOVERNANCE, Layer.L4_RISK, Corridor.POLICY_READ),
    (Layer.L5_GOVERNANCE, Layer.L6_PRESENTATION, Corridor.REPORT_READ),
    (Layer.L4_RISK, Layer.L6_PRESENTATION, Corridor.REPORT_READ),
    (Layer.L2_TEMPORAL, Layer.L6_PRESENTATION, Corridor.REPORT_READ),
    (Layer.L5_GOVERNANCE, Layer.L6_PRESENTATION, Corridor.EXTERNAL_ALERT),
})

_PRIVILEGED = frozenset({Corridor.DATA_WRITE, Corridor.CAPABILITY_REQUEST, Corridor.CAPABILITY_CONSUME})


class CorridorGate:
    """Fail-closed runtime gate for every cross-room interaction."""

    def __init__(self) -> None:
        self._seen_nonces: set[str] = set()

    def authorize(
        self,
        envelope: MessageEnvelope,
        *,
        destination: Room,
        authorized_identities: set[str] | frozenset[str] = frozenset(),
        capability: str | None = None,
        require_lineage: bool = True,
        consume_nonce: bool = True,
    ) -> tuple[bool, DenyReason | None]:
        key = (envelope.source_layer, envelope.destination_layer, envelope.corridor)
        if key not in _ALLOWED:
            return False, DenyReason.UNKNOWN_CORRIDOR
        if envelope.destination_room != destination.name or envelope.destination_layer != destination.layer:
            return False, DenyReason.LAYER_VIOLATION
        if envelope.source_identity not in authorized_identities and authorized_identities:
            return False, DenyReason.AUTHORIZATION_MISSING
        if not envelope.payload_schema or not envelope.payload_version:
            return False, DenyReason.SCHEMA_INVALID
        if require_lineage and envelope.source_artifact_sha is None:
            return False, DenyReason.LINEAGE_MISSING
        if not envelope.source_identity:
            return False, DenyReason.IDENTITY_MISMATCH
        if envelope.corridor in _PRIVILEGED and capability is None:
            return False, DenyReason.CAPABILITY_MISSING
        if envelope.nonce in self._seen_nonces:
            return False, DenyReason.REPLAY_DETECTED
        if consume_nonce:
            self._seen_nonces.add(envelope.nonce)
        return True, None

    def verify_return_identity(self, envelope: MessageEnvelope, destination: Room) -> tuple[bool, DenyReason | None]:
        if envelope.destination_room != destination.name or envelope.destination_layer != destination.layer:
            return False, DenyReason.IDENTITY_MISMATCH
        return True, None
