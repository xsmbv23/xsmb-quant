from data.reconciliation.reconciliation_gate_v1 import SourceObservation, reconcile


VALID_27 = tuple(str(i % 100) for i in range(27))
SHA_A = "a" * 64
SHA_B = "b" * 64


def test_duplicate_source_observation_is_denied():
    decision = reconcile([
        SourceObservation("ketqua16", VALID_27, SHA_A),
        SourceObservation("ketqua16", VALID_27, SHA_B),
    ])
    assert decision.state == "DENY"
    assert "DUPLICATE_SOURCE_OBSERVATION" in decision.reasons


def test_malformed_raw_hash_is_denied():
    decision = reconcile([
        SourceObservation("ketqua16", VALID_27, "not-a-sha256"),
        SourceObservation("xsmb", VALID_27, SHA_B),
    ])
    assert decision.state == "DENY"
    assert "INVALID_RAW_SHA256" in decision.reasons


def test_invalid_full27_is_denied():
    invalid = list(VALID_27)
    invalid[0] = "100"
    decision = reconcile([
        SourceObservation("ketqua16", tuple(invalid), SHA_A),
        SourceObservation("xsmb", VALID_27, SHA_B),
    ])
    assert decision.state == "DENY"
    assert "INVALID_FULL27_VALUE" in decision.reasons


def test_two_registered_independent_sources_can_form_candidate():
    decision = reconcile([
        SourceObservation("ketqua16", VALID_27, SHA_A),
        SourceObservation("xsmb", VALID_27, SHA_B),
    ])
    assert decision.state == "CANONICAL_CANDIDATE"
    assert decision.canonical_full27 == VALID_27
