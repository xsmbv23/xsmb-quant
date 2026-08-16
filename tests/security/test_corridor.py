from security.capability import CapabilityAuthority, CapabilityError
from security.corridor import Corridor, CorridorGate, Layer, MessageEnvelope, Room, DenyReason


def rooms():
    raw = Room("raw-source", Layer.L0_RAW, "crawler:ketqua16")
    data = Room("data-foundation", Layer.L1_DATA, "data-foundation:v1")
    quant = Room("quant", Layer.L3_QUANT, "quant:v1")
    risk = Room("risk", Layer.L4_RISK, "risk:v1")
    brain = Room("brain", Layer.L5_GOVERNANCE, "brain:v1")
    ui = Room("app", Layer.L6_PRESENTATION, "app-ui:v1")
    return raw, data, quant, risk, brain, ui


def test_valid_lower_to_upper_corridor():
    raw, data, *_ = rooms()
    env = MessageEnvelope.build(
        source=raw,
        destination=data,
        corridor=Corridor.DATA_READ,
        source_state="ACTIVE",
        payload_schema="RAW_SOURCE_V1",
        payload_version="1",
        payload={"artifact": "example"},
        source_artifact_sha="a" * 64,
    )
    ok, reason = CorridorGate().authorize(env, destination=data)
    assert ok is True
    assert reason is None


def test_unregistered_privilege_path_denied():
    raw, _, _, _, brain, _ = rooms()
    env = MessageEnvelope.build(
        source=raw,
        destination=brain,
        corridor=Corridor.GOVERNANCE_REQUEST,
        source_state="ACTIVE",
        payload_schema="RAW_SOURCE_V1",
        payload_version="1",
        payload={},
        source_artifact_sha="a" * 64,
    )
    ok, reason = CorridorGate().authorize(env, destination=brain)
    assert ok is False
    assert reason == DenyReason.UNKNOWN_CORRIDOR


def test_replay_is_denied():
    raw, data, *_ = rooms()
    env = MessageEnvelope.build(
        source=raw,
        destination=data,
        corridor=Corridor.DATA_READ,
        source_state="ACTIVE",
        payload_schema="RAW_SOURCE_V1",
        payload_version="1",
        payload={},
        source_artifact_sha="b" * 64,
    )
    gate = CorridorGate()
    assert gate.authorize(env, destination=data)[0] is True
    ok, reason = gate.authorize(env, destination=data)
    assert ok is False
    assert reason == DenyReason.REPLAY_DETECTED


def test_capability_is_scoped_and_one_shot():
    authority = CapabilityAuthority()
    cap = authority.issue(
        capability_type="HOLDOUT_MATERIALIZE",
        issuer_identity="brain:v1",
        subject_identity="executor:v1",
        source_room="brain",
        destination_room="executor",
        state="CAPABILITY_ISSUED",
    )
    authority.consume(
        cap.token,
        capability_type="HOLDOUT_MATERIALIZE",
        subject_identity="executor:v1",
        source_room="brain",
        destination_room="executor",
        state="CAPABILITY_ISSUED",
    )
    try:
        authority.consume(
            cap.token,
            capability_type="HOLDOUT_MATERIALIZE",
            subject_identity="executor:v1",
            source_room="brain",
            destination_room="executor",
            state="CAPABILITY_ISSUED",
        )
    except CapabilityError as exc:
        assert str(exc) == "CAPABILITY_REPLAY"
    else:
        raise AssertionError("replayed capability was accepted")


def test_lineage_is_required_by_default():
    raw, data, *_ = rooms()
    env = MessageEnvelope.build(
        source=raw,
        destination=data,
        corridor=Corridor.DATA_READ,
        source_state="ACTIVE",
        payload_schema="RAW_SOURCE_V1",
        payload_version="1",
        payload={},
    )
    ok, reason = CorridorGate().authorize(env, destination=data)
    assert ok is False
    assert reason == DenyReason.LINEAGE_MISSING
