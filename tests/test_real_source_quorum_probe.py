from data.reconciliation.reconciliation_gate_v1 import SourceObservation, reconcile


VALID_27 = tuple(str(i % 100) for i in range(27))


def test_probe_admission_requires_registry_independence():
    decision = reconcile([
        SourceObservation("ketqua16", VALID_27, "a" * 64),
        SourceObservation("xsmb", VALID_27, "b" * 64),
    ], minimum_independent_sources=2)
    assert decision.state == "CANONICAL_CANDIDATE"


def test_probe_admission_denies_same_source_quorum():
    decision = reconcile([
        SourceObservation("ketqua16", VALID_27, "a" * 64),
        SourceObservation("ketqua16", VALID_27, "b" * 64),
    ], minimum_independent_sources=2)
    assert decision.state == "DENY"
    assert "DUPLICATE_SOURCE_OBSERVATION" in decision.reasons
