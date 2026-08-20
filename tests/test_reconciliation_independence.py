import unittest

from data.reconciliation.reconciliation_gate_v1 import SourceObservation, reconcile


FULL27 = tuple(str(i).zfill(2) for i in range(27))


class ReconciliationIndependenceTests(unittest.TestCase):
    def test_same_source_cannot_satisfy_quorum(self):
        observations = [
            SourceObservation("ketqua16", FULL27, "a" * 64),
            SourceObservation("ketqua16", FULL27, "b" * 64),
        ]
        decision = reconcile(observations)
        self.assertEqual(decision.state, "DENY")
        self.assertIn("QUORUM_NOT_MET", decision.reasons)

    def test_distinct_registered_independence_groups_can_satisfy_quorum(self):
        observations = [
            SourceObservation("ketqua16", FULL27, "a" * 64),
            SourceObservation("xsmb", FULL27, "b" * 64),
        ]
        decision = reconcile(observations)
        self.assertEqual(decision.state, "CANONICAL_CANDIDATE")
        self.assertEqual(decision.canonical_full27, FULL27)

    def test_unregistered_source_is_denied(self):
        observations = [
            SourceObservation("unregistered", FULL27, "a" * 64),
            SourceObservation("ketqua16", FULL27, "b" * 64),
        ]
        decision = reconcile(observations)
        self.assertEqual(decision.state, "DENY")
        self.assertTrue(any(reason.startswith("UNREGISTERED_SOURCE:") for reason in decision.reasons))

    def test_invalid_quorum_is_denied(self):
        decision = reconcile([SourceObservation("ketqua16", FULL27, "a" * 64)], minimum_independent_sources=0)
        self.assertEqual(decision.state, "DENY")
        self.assertIn("INVALID_MINIMUM_INDEPENDENT_SOURCES", decision.reasons)


if __name__ == "__main__":
    unittest.main()
