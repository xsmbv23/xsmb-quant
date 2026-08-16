from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from typing import Any


_SECRET_KEYS = {
    "password", "passwd", "token", "secret", "api_key", "apikey",
    "database_url", "internal_database_url", "external_database_url",
    "authorization", "credential", "credentials",
}


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if key.lower() in _SECRET_KEYS else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


@dataclass(frozen=True)
class CommunicationAuditEvent:
    communication_id: str
    source_room: str
    source_layer: str
    destination_room: str
    destination_layer: str
    corridor_type: str
    message_schema: str
    source_state: str
    decision: str
    reason_code: str | None
    source_artifact_sha: str | None
    policy_manifest_sha: str | None
    timestamp: str

    def to_json(self) -> str:
        return json.dumps(redact(asdict(self)), sort_keys=True, separators=(",", ":"))


class AppendOnlyCommunicationAudit:
    """In-memory append-only sink; persistence belongs to the evidence layer."""

    def __init__(self) -> None:
        self._events: list[CommunicationAuditEvent] = []

    def append(self, event: CommunicationAuditEvent) -> None:
        self._events.append(event)

    def record(self, *, envelope, decision: str, reason_code: str | None) -> CommunicationAuditEvent:
        event = CommunicationAuditEvent(
            communication_id=envelope.message_id,
            source_room=envelope.source_room,
            source_layer=envelope.source_layer.value,
            destination_room=envelope.destination_room,
            destination_layer=envelope.destination_layer.value,
            corridor_type=envelope.corridor.value,
            message_schema=envelope.payload_schema,
            source_state=envelope.source_state,
            decision=decision,
            reason_code=reason_code,
            source_artifact_sha=envelope.source_artifact_sha,
            policy_manifest_sha=envelope.policy_manifest_sha,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.append(event)
        return event

    def events(self) -> tuple[CommunicationAuditEvent, ...]:
        return tuple(self._events)
