from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import secrets


class CapabilityError(RuntimeError):
    pass


@dataclass(frozen=True)
class Capability:
    token: str
    capability_type: str
    issuer_identity: str
    subject_identity: str
    source_room: str
    destination_room: str
    state: str
    issued_at: datetime
    expires_at: datetime
    single_use: bool = True


class CapabilityAuthority:
    """Single in-process authority for scoped, opaque, one-shot capabilities.

    Persistence/signing can be added later behind this interface. Callers must
    never infer authority from booleans or runtime state alone.
    """

    def __init__(self) -> None:
        self._active: dict[str, Capability] = {}
        self._consumed: set[str] = set()

    def issue(
        self,
        *,
        capability_type: str,
        issuer_identity: str,
        subject_identity: str,
        source_room: str,
        destination_room: str,
        state: str,
        ttl_seconds: int = 300,
        single_use: bool = True,
    ) -> Capability:
        if ttl_seconds <= 0:
            raise CapabilityError("CAPABILITY_TTL_INVALID")
        now = datetime.now(timezone.utc)
        cap = Capability(
            token=secrets.token_urlsafe(32),
            capability_type=capability_type,
            issuer_identity=issuer_identity,
            subject_identity=subject_identity,
            source_room=source_room,
            destination_room=destination_room,
            state=state,
            issued_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
            single_use=single_use,
        )
        self._active[cap.token] = cap
        return cap

    def consume(
        self,
        token: str,
        *,
        capability_type: str,
        subject_identity: str,
        source_room: str,
        destination_room: str,
        state: str,
    ) -> Capability:
        if token in self._consumed:
            raise CapabilityError("CAPABILITY_REPLAY")
        cap = self._active.get(token)
        if cap is None:
            raise CapabilityError("CAPABILITY_UNKNOWN")
        now = datetime.now(timezone.utc)
        if now >= cap.expires_at:
            self.revoke(token)
            raise CapabilityError("CAPABILITY_EXPIRED")
        if (
            cap.capability_type != capability_type
            or cap.subject_identity != subject_identity
            or cap.source_room != source_room
            or cap.destination_room != destination_room
            or cap.state != state
        ):
            raise CapabilityError("CAPABILITY_SCOPE_MISMATCH")
        if cap.single_use:
            self._consumed.add(token)
            self._active.pop(token, None)
        return cap

    def revoke(self, token: str) -> None:
        self._active.pop(token, None)
        self._consumed.add(token)

    def clear_all(self) -> None:
        for token in tuple(self._active):
            self.revoke(token)
