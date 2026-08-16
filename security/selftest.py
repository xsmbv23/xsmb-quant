from __future__ import annotations

from .capability import CapabilityAuthority, CapabilityError
from .corridor import Corridor, CorridorGate, DenyReason, Layer, MessageEnvelope, Room
from .fail_closed import terminal_halt


def run_security_selftest() -> dict[str, object]:
    raw = Room("raw-source", Layer.L0_RAW, "crawler:selftest")
    data = Room("data-foundation", Layer.L1_DATA, "data-foundation:v1")
    brain = Room("brain", Layer.L5_GOVERNANCE, "brain:v1")

    gate = CorridorGate()
    env = MessageEnvelope.build(
        source=raw,
        destination=data,
        corridor=Corridor.DATA_READ,
        source_state="ACTIVE",
        payload_schema="RAW_SOURCE_V1",
        payload_version="1",
        payload={"fixture": "security-selftest"},
        source_artifact_sha="a" * 64,
    )
    ok, reason = gate.authorize(env, destination=data)
    assert ok and reason is None

    ok, reason = gate.authorize(env, destination=data)
    assert not ok and reason == DenyReason.REPLAY_DETECTED

    privileged = MessageEnvelope.build(
        source=raw,
        destination=brain,
        corridor=Corridor.GOVERNANCE_REQUEST,
        source_state="ACTIVE",
        payload_schema="RAW_SOURCE_V1",
        payload_version="1",
        payload={},
        source_artifact_sha="b" * 64,
    )
    ok, reason = CorridorGate().authorize(privileged, destination=brain)
    assert not ok and reason == DenyReason.UNKNOWN_CORRIDOR

    authority = CapabilityAuthority()
    cap = authority.issue(
        capability_type="SELFTEST",
        issuer_identity="brain:v1",
        subject_identity="executor:v1",
        source_room="brain",
        destination_room="executor",
        state="CAPABILITY_ISSUED",
    )
    authority.consume(
        cap.token,
        capability_type="SELFTEST",
        subject_identity="executor:v1",
        source_room="brain",
        destination_room="executor",
        state="CAPABILITY_ISSUED",
    )
    try:
        authority.consume(
            cap.token,
            capability_type="SELFTEST",
            subject_identity="executor:v1",
            source_room="brain",
            destination_room="executor",
            state="CAPABILITY_ISSUED",
        )
    except CapabilityError as exc:
        assert str(exc) == "CAPABILITY_REPLAY"
    else:
        raise AssertionError("capability replay accepted")

    halt = terminal_halt("SECURITY_SELFTEST_PRIVILEGE_FAILURE")
    assert halt.status == "TERMINAL_HALT"
    assert halt.promotion == "DENY"
    assert halt.action == "HALT"

    return {
        "status": "RUNTIME_VERIFIED",
        "promotion": "DENY",
        "checks": [
            "valid_corridor",
            "replay_denied",
            "unknown_corridor_denied",
            "capability_replay_denied",
            "terminal_halt_fail_closed",
        ],
    }
